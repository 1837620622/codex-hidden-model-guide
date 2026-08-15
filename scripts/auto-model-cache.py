#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Codex 模型目录自动同步脚本(跨平台 macOS / Linux / Windows)
- 优先直连官方源 /backend-api/codex/models 拉取最新模型目录(实时,不等本地缓存刷新)
- 官方源不可用时回退读取本地 models_cache.json
- 将目录中所有 visibility=hide 的隐藏模型强制改为 list(不硬编码模型名,
  官方新增任何隐藏模型都会自动可见)
- 无变化时零操作,有变化时原子写入并记录日志
- 只写可见目录文件,不修改 models_cache.json / config.toml 等任何其他配置

路径识别优先级:
  1. 命令行参数: python3 auto-model-cache.py <CODEX_ROOT>
  2. 环境变量 CODEX_HOME
  3. 默认回退 ~/.codex(macOS/Linux)或 %USERPROFILE%\\.codex(Windows)

Windows 注意:所有文件读写显式指定 UTF-8 编码,避免 GBK 乱码。
"""

import json
import os
import shutil
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

# 跨平台进程锁:macOS/Linux 用 fcntl,Windows 用 msvcrt
# 防止 launchd/cron/计划任务与手动运行同时执行时相互竞争
try:
    import fcntl
    _LOCK = fcntl
    _LOCK_MODE = "fcntl"
except ImportError:
    try:
        import msvcrt
        _LOCK = msvcrt
        _LOCK_MODE = "msvcrt"
    except ImportError:
        _LOCK = None
        _LOCK_MODE = "none"


def resolve_codex_root(argv):
    """按 命令行参数 > CODEX_HOME > 默认路径 的优先级解析 Codex 根目录"""
    if len(argv) > 1 and argv[1].strip():
        return os.path.abspath(argv[1])
    env = os.environ.get("CODEX_HOME")
    if env and env.strip():
        return os.path.abspath(env)
    return os.path.expanduser("~/.codex")


CODEX_HOME = resolve_codex_root(sys.argv)
CACHE_PATH = os.path.join(CODEX_HOME, "models_cache.json")
VISIBLE_PATH = os.path.join(CODEX_HOME, "models_auto_visible.json")
LOG_DIR = os.path.join(CODEX_HOME, "log")
LOG_PATH = os.path.join(LOG_DIR, "auto-model-cache.log")
LOG_MAX_BYTES = 1024 * 1024  # 主日志超过 1MB 时轮转
LOG_KEEP_DAYS = 7  # 日志保留天数,超过自动删除


def cleanup_logs():
    """清理日志:主日志超过 1MB 轮转为 .old;删除超过保留天数的旧日志"""
    try:
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > LOG_MAX_BYTES:
            shutil.move(LOG_PATH, LOG_PATH + ".old")
        cutoff = time.time() - LOG_KEEP_DAYS * 86400
        for name in os.listdir(LOG_DIR):
            # 只清理本脚本自己的日志,不碰 launchd 的 stdout/stderr 日志
            if name not in ("auto-model-cache.log", "auto-model-cache.log.old"):
                continue
            path = os.path.join(LOG_DIR, name)
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
    except Exception:
        pass


def log(msg):
    """追加一行日志,自动创建日志目录;写日志前先清理。
    日志写入失败不影响主流程(绝不因日志问题崩溃)"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        cleanup_logs()
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    except Exception:
        pass


_LOCK_FILE = None  # 进程锁文件句柄,获取锁后持有


def acquire_lock():
    """非阻塞获取进程锁,防止并发执行;拿不到锁说明已有实例在运行,返回 False"""
    global _LOCK_FILE
    if _LOCK is None:
        return True
    lock_path = os.path.join(LOG_DIR, "auto-model-cache.lock")
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        f = open(lock_path, "a", encoding="utf-8")
        if _LOCK_MODE == "fcntl":
            _LOCK.flock(f, _LOCK.LOCK_EX | _LOCK.LOCK_NB)
        else:
            _LOCK.locking(f.fileno(), _LOCK.LK_NBLCK, 1)
    except OSError:
        try:
            f.close()
        except Exception:
            pass
        log("提示: 已有实例在运行, 本次跳过")
        return False
    _LOCK_FILE = f
    return True


def release_lock():
    """释放进程锁,同时清理锁文件"""
    global _LOCK_FILE
    if _LOCK_FILE is None:
        return
    try:
        if _LOCK_MODE == "fcntl":
            _LOCK.flock(_LOCK_FILE, _LOCK.LOCK_UN)
        else:
            _LOCK.locking(_LOCK_FILE.fileno(), _LOCK.LK_UNLCK, 1)
    except Exception:
        pass
    try:
        _LOCK_FILE.close()
    except Exception:
        pass
    _LOCK_FILE = None
    try:
        os.remove(os.path.join(LOG_DIR, "auto-model-cache.lock"))
    except Exception:
        pass


def load_json(path):
    """读取 JSON 文件,显式 UTF-8,失败时抛出异常"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_official_catalog():
    """直连官方源拉取最新模型目录,返回 (目录dict, 来源描述)。
    失败(网络/认证/解析)时返回 (None, 原因)。绝不写任何本地文件。
    数据来源: Codex CLI 同款端点 /backend-api/codex/models,
    认证取 auth.json 的 access_token,版本号取本地缓存的 client_version。
    """
    try:
        # 读取认证令牌
        auth_path = os.path.join(CODEX_HOME, "auth.json")
        if not os.path.exists(auth_path):
            return None, "auth.json 不存在"
        auth = load_json(auth_path)
        tokens = auth.get("tokens") or {}
        token = tokens.get("access_token") or auth.get("OPENAI_API_KEY")
        if not token:
            return None, "auth.json 中无 access_token"

        # 读取本地缓存中的 client_version(与客户端一致,避免版本门禁静默过滤)
        client_version = None
        if os.path.exists(CACHE_PATH):
            try:
                client_version = load_json(CACHE_PATH).get("client_version")
            except Exception:
                pass
        if not client_version:
            return None, "无法确定 client_version"

        url = "https://chatgpt.com/backend-api/codex/models?client_version={}".format(
            client_version)
        req = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "OpenAI-Build": "macos_cli",
            "User-Agent": "codex/" + str(client_version),
            "Accept": "application/json",
        })
        # 有限超时,失败不阻塞定时任务
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            body = resp.read()
        data = json.loads(body.decode("utf-8"))
        if "models" not in data or not isinstance(data["models"], list):
            return None, "官方源返回缺少 models 列表"
        if not data["models"]:
            return None, "官方源返回空模型列表"
        return data, "官方源"
    except urllib.error.HTTPError as e:
        return None, "官方源 HTTP {}".format(e.code)
    except urllib.error.URLError as e:
        return None, "官方源网络错误: {}".format(getattr(e, "reason", e))
    except Exception as e:
        return None, "官方源解析失败: {}".format(e)


def main():
    # 已有实例在运行(launchd/cron/计划任务/手动并发)时直接退出,避免竞争
    if not acquire_lock():
        sys.exit(0)

    try:
        # 清理上次崩溃可能遗留的临时文件,防止误读半成品
        try:
            stale = [n for n in os.listdir(os.path.dirname(VISIBLE_PATH))
                     if n.startswith(os.path.basename(VISIBLE_PATH) + ".tmp")]
            for n in stale:
                os.remove(os.path.join(os.path.dirname(VISIBLE_PATH), n))
        except OSError:
            pass

        # 优先直连官方源拉取最新目录(实时,不等本地缓存刷新)
        cache = None
        catalog, err = fetch_official_catalog()
        if catalog is not None:
            cache = catalog
            source = "官方源"
        else:
            # 官方源不可用(网络/认证/版本未知)时回退本地缓存
            log("官方源不可用({}), 回退本地缓存".format(err))
            if not os.path.exists(CACHE_PATH):
                log(f"错误: 缓存不存在 {CACHE_PATH}")
                sys.exit(1)
            try:
                cache = load_json(CACHE_PATH)
            except Exception as e:
                log(f"错误: 缓存解析失败 {e}, 保留现有目录")
                sys.exit(1)
            source = "本地缓存"

        if "models" not in cache or not isinstance(cache["models"], list):
            log("错误: 目录缺少 models 列表, 保留现有目录")
            sys.exit(1)
        if not cache["models"]:
            log("错误: 目录为空, 保留现有目录")
            sys.exit(1)

        # 深度复制后应用可见性覆盖,不修改原始缓存对象
        visible = json.loads(json.dumps(cache))
        changed = []
        for m in visible["models"]:
            if m.get("visibility") == "hide":
                m["visibility"] = "list"
                changed.append(m.get("slug"))

        # 记录新旧 slug 集合,用于对比新增/移除
        old_slugs = set()
        if os.path.exists(VISIBLE_PATH):
            try:
                old = load_json(VISIBLE_PATH)
                old_slugs = {m.get("slug") for m in old.get("models", [])}
            except Exception:
                pass
        new_slugs = {m.get("slug") for m in visible["models"]}
        added = sorted(new_slugs - old_slugs)
        removed = sorted(old_slugs - new_slugs)

        # 无任何差异且目标文件存在时零操作,避免无谓写入
        if os.path.exists(VISIBLE_PATH):
            try:
                old = load_json(VISIBLE_PATH)
                if old == visible:
                    log(f"无变化, 跳过写入 (模型 {len(new_slugs)} 个)")
                    return
            except Exception:
                pass

        # 原子写入:临时文件带 pid 后缀,多实例并发不会互相覆盖
        # os.replace 跨平台原子;Windows 上目标已存在时 shutil.move 会退化为
        # 非原子的 copy+unlink,中途崩溃会损坏文件,故不用 shutil.move
        tmp = "{}.tmp.{}".format(VISIBLE_PATH, os.getpid())
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(visible, f, ensure_ascii=False, indent=2)
            os.replace(tmp, VISIBLE_PATH)
        except Exception as e:
            log(f"错误: 写入失败 {e}")
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            sys.exit(1)

        log(f"已同步({source}) {len(new_slugs)} 个模型; 隐藏→可见: {changed or '无'}; "
            f"新增: {added or '无'}; 移除: {removed or '无'}")
    finally:
        release_lock()


if __name__ == "__main__":
    main()