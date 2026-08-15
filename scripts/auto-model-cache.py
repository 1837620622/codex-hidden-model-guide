#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Codex 模型目录自动同步脚本(跨平台 macOS / Windows)
- 读取官方 models_cache.json,重新生成可见模型目录
- 将目录中所有 visibility=hide 的隐藏模型强制改为 list(不硬编码模型名,
  以后官方新增任何隐藏模型都会自动可见)
- 无变化时零操作,有变化时原子写入并记录日志
- 只写可见目录文件,不修改任何其他配置

路径识别优先级:
  1. 命令行参数: python3 auto-model-cache.py <CODEX_ROOT>
  2. 环境变量 CODEX_HOME
  3. 默认回退 ~/.codex(macOS)或 %USERPROFILE%\\.codex(Windows)

Windows 注意:所有文件读写显式指定 UTF-8 编码,避免 GBK 乱码。
"""

import json
import os
import shutil
import sys
import time
from datetime import datetime


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
    """追加一行日志,自动创建日志目录;写日志前先清理"""
    os.makedirs(LOG_DIR, exist_ok=True)
    cleanup_logs()
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")


def load_json(path):
    """读取 JSON 文件,显式 UTF-8,失败时抛出异常"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    # 缓存不存在时直接失败,保留现有可见目录
    if not os.path.exists(CACHE_PATH):
        log(f"错误: 缓存不存在 {CACHE_PATH}")
        sys.exit(1)

    # 缓存解析失败时直接失败,保留现有可见目录
    try:
        cache = load_json(CACHE_PATH)
    except Exception as e:
        log(f"错误: 缓存解析失败 {e}, 保留现有目录")
        sys.exit(1)

    if "models" not in cache or not isinstance(cache["models"], list):
        log("错误: 缓存缺少 models 列表, 保留现有目录")
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

    # 原子写入:先写临时文件再 os.replace 替换
    # os.replace 跨平台原子;Windows 上目标已存在时 shutil.move 会退化为
    # 非原子的 copy+unlink,中途崩溃会损坏文件,故不用 shutil.move
    tmp = VISIBLE_PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(visible, f, ensure_ascii=False, indent=2)
        os.replace(tmp, VISIBLE_PATH)
    except Exception as e:
        log(f"错误: 写入失败 {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
        sys.exit(1)

    log(f"已同步 {len(new_slugs)} 个模型; 隐藏→可见: {changed or '无'}; "
        f"新增: {added or '无'}; 移除: {removed or '无'}")


if __name__ == "__main__":
    main()