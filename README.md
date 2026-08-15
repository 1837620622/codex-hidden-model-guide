# Codex 隐藏路由模型无限调用指南

> 隐藏路由模型(当前示例:`gpt-5.6-sol-wm`)全平台启用教程
> 任意付费账号不消耗额度,附每小时自动同步脚本

<div align="center">

**适用平台:macOS / Linux / Windows** | **适用账号:Plus / Pro / Team**

</div>

> **通用性说明**:本文以 `gpt-5.6-sol-wm` 作为示例。OpenAI 会不定期下发新的隐藏路由模型,本文方法对所有隐藏模型通用——只需把文中出现的 slug 换成你本地缓存里的实际值(如何查找见[第 2 步](#第-2-步查找本地缓存的隐藏模型))。自动同步脚本不硬编码任何模型名,未来新模型自动生效。

---

## 目录

- [这是什么](#这是什么)
- [原理](#原理)
- [前置条件](#前置条件)
- [一键安装(推荐)](#一键安装推荐)
- [手动配置步骤](#手动配置步骤)
- [服务器最小探针](#服务器最小探针)
- [自动同步脚本](#自动同步脚本)
- [为什么不消耗额度](#为什么不消耗额度)
- [常见问题 FAQ](#常见问题-faq)
- [回滚方法](#回滚方法)
- [支持与赞赏](#支持与赞赏)
- [目录结构](#目录结构)

---

## 这是什么

`gpt-5.6-sol-wm`(示例,下称"隐藏路由模型")是 OpenAI 服务器主动下发到所有 Codex 客户端模型目录中的一个**内部路由别名**,但默认隐藏(`visibility: hide`)。这类模型是官方下发给客户端的隐藏条目,不属于公开 API 模型。

核心结论:

- 不是 API 调用,不走 API 计费通道
- 不出现在 OpenAI 消费明细中
- Plus / Pro / Team 账号均可用
- Free 账号会被服务器拒绝(本地配置无法绕过)
- 返回内容质量与对应的公开模型完全一致

## 原理

```mermaid
graph LR
    A[Codex 启动] --> B[读取模型目录]
    B --> C{model_catalog_json 已配置?}
    C -->|否| D[官方 models_cache.json]
    C -->|是| E[本地 models_auto_visible.json]
    D --> F[隐藏模型 hide 不可见]
    E --> G[隐藏模型改为 list 可见]
    G --> H[选择器中可见,按次选用]
    H --> I[不消耗额度]
```

| 属性 | 值 | 含义 |
| --- | --- | --- |
| slug | `gpt-5.6-sol-wm`(示例) | 模型内部标识,以本地缓存实际值为准 |
| visibility | `hide` | 默认在模型选择器中隐藏 |
| supported_in_api | `false` | 不是公开 API 模型,不走 API 计费通道 |
| 存在位置 | `models_cache.json` | 由 OpenAI 服务器自动下发 |

两个独立的判断:

1. **本地显示**:把 `visibility` 从 `hide` 改成 `list`,只是让模型选择器显示出来
2. **服务器授权**:账号是否有权限调用,完全由服务器决定

改本地目录不等于获得权限,但实测所有非 Free 账号都能成功调用。

## 前置条件

| 项目 | 要求 |
| --- | --- |
| Codex Desktop 或 CLI | 已安装且能正常使用 |
| ChatGPT 账号 | Plus / Pro / Team 任意付费方案 |
| Python 3 | 仅自动同步脚本需要(手动配置不需要) |

## 一键安装(推荐)

> 安装器自动识别 CODEX_ROOT(命令行参数 > CODEX_HOME > 默认路径),自动完成:安装脚本 → 生成可见目录 → 注册定时任务。

**自动安装到 Codex 根目录(默认 `~/.codex`,macOS/Linux;Windows 为 `%USERPROFILE%\.codex`):**

| 文件 | 位置 | 说明 |
| --- | --- | --- |
| `auto-model-cache.py` | `<CODEX_ROOT>/` | 自动同步脚本(可执行) |
| `models_auto_visible.json` | `<CODEX_ROOT>/` | 可见模型目录(自动生成) |
| `auto-model-cache.log` | `<CODEX_ROOT>/log/` | 运行日志(1MB 轮转 + 7 天自动清理) |
| 定时任务 | launchd / cron / 计划任务 | 每小时运行一次 |

自定义 CODEX_ROOT:安装时传参数即可,见下方示例。

> 下表是"装了什么";总改动清单(含 config.toml 两行)见[改动最小化](#改动最小化)。

### macOS / Linux

```bash
chmod +x install.sh
./install.sh
```

自定义路径:

```bash
./install.sh /自定义/codex路径
```

> install.sh 自动检测系统:macOS 注册 launchd(每小时 + 登录时运行),Linux 注册 crontab(每小时),均自动处理路径、清理旧任务。

### 改动最小化

本教程对系统的改动仅限以下几项,其余文件与配置一律不动,回滚时删除这几项即可完全还原:

| 改动项 | 位置 | 用途 |
| --- | --- | --- |
| `config.toml` 加 1 行 | `<CODEX_ROOT>/config.toml` | 指向可见目录(不改动原有 model) |
| 可见目录 1 个 | `<CODEX_ROOT>/models_auto_visible.json` | 所有隐藏模型改为可见 |
| 同步脚本 1 个 | `<CODEX_ROOT>/auto-model-cache.py` | 每小时自动同步(可选,不装也能用) |
| 定时任务 1 个 | launchd / cron / 计划任务 | 每小时跑一次脚本(可选) |

- 不改 `models_cache.json`(会被官方自动覆盖)
- 不改认证、权限、网络等任何其他配置
- 同步脚本只把 `visibility` 从 `hide` 改为 `list`,其他字段一律保留原样

### Windows(管理员 PowerShell)

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

自定义路径:

```powershell
.\install.ps1 'D:\自定义\codex路径'
```

> Windows 注意:安装器已内置 UTF-8 编码处理与管理员权限检查,中文系统(GBK 默认编码)下不会乱码。

## 手动配置步骤

### 第 1 步:确认 CODEX_ROOT 路径

**Windows(PowerShell):**

```powershell
$CodexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$CodexRoot
```

**macOS / Linux(终端):**

```bash
echo "${CODEX_HOME:-$HOME/.codex}"
```

### 第 2 步:查找本地缓存的隐藏模型

先确认隐藏路由模型存在。把下面的 `gpt-5.6-sol-wm` 换成你想启用的 slug(当前示例;以后新下发模型的 slug 可能不同,同样适用):

**Windows:**

```powershell
$CachePath = Join-Path $CodexRoot 'models_cache.json'
Select-String -LiteralPath $CachePath -Pattern '"slug": "gpt-5.6-sol-wm"'
```

**macOS / Linux:**

```bash
grep -o '"slug": "gpt-5.6-sol-wm"' "${CODEX_HOME:-$HOME/.codex}/models_cache.json"
```

看到了目标 slug 且附近有 `"visibility": "hide"`:继续下一步。完全找不到:先正常使用一次 Codex 让它刷新缓存,然后再查。

> 提示:若 `models_cache.json` 是压缩格式(无空格),把搜索模式改为 `"slug":"gpt-5.6-sol-wm"` 或直接用 `grep -o 'gpt-5\.6-sol-wm'`。

### 第 3 步:生成可见模型目录(核心操作)

> 重要:先彻底退出 Codex,包括系统托盘/菜单栏那个小图标。

**Windows(PowerShell,完整脚本):**

```powershell
$CodexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$CachePath = Join-Path $CodexRoot 'models_cache.json'
$VisibleCatalog = Join-Path $CodexRoot 'models_auto_visible.json'
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$CacheBackup = Join-Path $CodexRoot "models_cache.before-hidden-$Stamp.bak"

if (-not (Test-Path -LiteralPath $CachePath)) { throw "找不到模型缓存: $CachePath" }

# 备份原始缓存
Copy-Item -LiteralPath $CachePath -Destination $CacheBackup
# 复制一份作为自定义目录
Copy-Item -LiteralPath $CachePath -Destination $VisibleCatalog -Force

# 把所有 hide 改为 list(以 UTF-8 读写,避免中文系统 GBK 乱码)
$Raw = [IO.File]::ReadAllText($VisibleCatalog, [Text.Encoding]::UTF8)
$Updated = $Raw -replace '("visibility"\s*:\s*)"hide"', '$1"list"'
[IO.File]::WriteAllText($VisibleCatalog, $Updated, [Text.UTF8Encoding]::new($false))

Write-Host "已生成: $VisibleCatalog"
Write-Host "原始缓存备份: $CacheBackup"
```

**macOS(终端):**

```bash
python3 - <<'PY'
import json, os
root = os.environ.get('CODEX_HOME') or os.path.expanduser('~/.codex')
cache = json.load(open(os.path.join(root, 'models_cache.json'), encoding='utf-8'))
for m in cache['models']:
    if m.get('visibility') == 'hide':
        m['visibility'] = 'list'
out = os.path.join(root, 'models_auto_visible.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)
print('已生成:', out)
PY
```

要点:

- `model_catalog_json` 是**整目录替换**而不是合并,必须复制完整缓存再修改
- 只需要改 `visibility` 一个字段,其他字段一律保留
- 不要直接改 `models_cache.json`,Codex 会自动刷新覆盖它

### 第 4 步:验证没有误改

**Windows:**

```powershell
$Catalog = Get-Content -Raw -LiteralPath $VisibleCatalog -Encoding UTF8 | ConvertFrom-Json -Depth 100
@($Catalog.models | Where-Object slug -eq 'gpt-5.6-sol-wm').visibility
```

预期输出:`list`(换成你目标的 slug 查询)

**macOS / Linux:**

```bash
python3 -c "
import json, os
root = os.environ.get('CODEX_HOME') or os.path.expanduser('~/.codex')
d = json.load(open(os.path.join(root, 'models_auto_visible.json'), encoding='utf-8'))
for m in d['models']:
    print(m['slug'], m['visibility'])
"
```

预期输出:目标 slug 为 `list`,所有原隐藏模型均为 `list`(含 codex-auto-review),原可见模型保持 `list` 不变。

### 第 5 步:修改 config.toml(只加一行,不设默认模型)

> 建议先备份:`cp "${CODEX_HOME:-$HOME/.codex}/config.toml" "${CODEX_HOME:-$HOME/.codex}/config.toml.before-hidden-$(date +%Y%m%d-%H%M%S).bak"`(Windows 用 `Copy-Item`,回滚时可用)。
>
> 只需在顶层添加 `model_catalog_json` 一行,其余配置一律不动(路径替换成你自己的,先用第 1 步的 `$CodexRoot` 查看实际路径):

> Windows 路径中的斜杠正反均可,Codex 均能识别;但需写完整路径,不能用 `$CodexRoot` 变量(TOML 不支持变量)。

**Windows 示例:**

```toml
model_catalog_json = "C:/Users/你的用户名/.codex/models_auto_visible.json"
```

**macOS / Linux 示例:**

```toml
model_catalog_json = "/Users/你的用户名/.codex/models_auto_visible.json"
```

**为什么只加这一行、不设默认模型:**

- 隐藏路由模型是隐藏条目,只要 `model_catalog_json` 指向可见目录,它就会出现在 Codex 的模型选择器中
- 每次使用时在模型选择器中**自主选择**隐藏路由模型即可,不需要也不建议写进 `model = "..."` 默认值
- 隐藏路由模型可能随时失效;设为默认模型后一旦失效,整个 Codex 都会无法使用,需要手动改配置才能恢复
- 不设默认模型,即使隐藏路由模型失效,Codex 也始终可用,随时切换回正常模型即可

> 可选(不建议,了解即可):如确要设为默认模型,可添加 `model = "你的隐藏路由slug"`,并知晓上述失效风险。不要动其他任何配置(不要改 `supported_in_api`,那个字段不影响 Codex 调用)。

> 可选(不影响本教程效果,非必需):如想加深推理可加 `model_reasoning_effort = "max"`;如想开启快速模式可加 `service_tier = "fast"` + `[features] fast_mode = true`。不熟悉 TOML 语法的话建议跳过。

### 第 6 步:重启 Codex 并在选择器中选择

1. 从系统托盘/菜单栏彻底退出 Codex(不是点窗口右上角关闭)
2. 重新打开 Codex
3. 新建任务,打开模型选择器
4. 你应该能看到目标模型(如 GPT-5.6-Sol-WM)出现在列表中,**选中它**即可使用

> 隐藏路由模型只在选择器中按次选用,不设为默认,失效后随时切回正常模型。

如果选择器里还是看不到,可以用 CLI 检查(视版本支持情况而定):

```bash
codex debug models
```

在输出中搜索目标 slug(如 `gpt-5.6-sol-wm`),看看 visibility 是不是 `list`。若该子命令不可用,直接跳到下面的服务器探针验证。

### 第 7 步:不改 UI 也能用

如果你不想改模型选择器,也可以直接用命令行指定模型(换成你的 slug):

```bash
codex --model gpt-5.6-sol-wm
```

你的 `config.toml` 中原有的 `model` 默认值保持不动,新建任务时默认仍用你原来的模型;需要时在选择器中选中隐藏路由模型即可,不用每次写 `--model`。

## 服务器最小探针

跑一次这个最小探针,确认服务器接受你的账号(把 `gpt-5.6-sol-wm` 换成你的 slug):

**macOS / Linux:**

```bash
codex --ask-for-approval never exec \
  --ignore-user-config \
  --ephemeral \
  --json \
  --skip-git-repo-check \
  -C "$TMPDIR" \
  --sandbox read-only \
  --model gpt-5.6-sol-wm \
  -c 'model_reasoning_effort="low"' \
  -c 'approval_policy="never"' \
  -c 'web_search="disabled"' \
  -c 'features.shell_tool=false' \
  -c 'features.multi_agent=false' \
  -c 'project_doc_max_bytes=0' \
  'Reply exactly HIDDEN_OK. Do not call any tool.'
```

**Windows(PowerShell,换行符用反引号):**

```powershell
codex --ask-for-approval never exec `
  --ignore-user-config `
  --ephemeral `
  --json `
  --skip-git-repo-check `
  -C $env:TEMP `
  --sandbox read-only `
  --model gpt-5.6-sol-wm `
  -c 'model_reasoning_effort="low"' `
  -c 'approval_policy="never"' `
  -c 'web_search="disabled"' `
  -c 'features.shell_tool=false' `
  -c 'features.multi_agent=false' `
  -c 'project_doc_max_bytes=0' `
  'Reply exactly HIDDEN_OK. Do not call any tool.'
```

| 输出 | 含义 |
| --- | --- |
| `HIDDEN_OK` + 退出码 0 | 服务器接受了你的账号,可以正常使用 |
| `model is not supported` | 你的账号没有权限(大概率是 Free 账号) |
| 401 错误 | 登录过期了,重新登录 |
| 额度超限 | 不能据此判断隐藏路由模型是否可用 |

## 自动同步脚本

官方缓存会定期刷新。脚本自动检测 `models_cache.json` 变化,重新生成可见目录,官方新增的任何隐藏模型都会自动变为可见,无需手动操作。跨平台纯 Python 实现,macOS / Linux / Windows 通用。

**路径识别优先级**(官方约定,三处一致,无硬编码):

1. 命令行参数:`auto-model-cache.py <CODEX_ROOT>`
2. 环境变量 `CODEX_HOME`(官方文档:默认 `~/.codex`,设置时目录必须已存在)
3. 默认回退:`~/.codex`(macOS/Linux)/ `%USERPROFILE%\.codex`(Windows)

依据 OpenAI 官方文档(https://developers.openai.com/codex/environment-variables):`CODEX_HOME` 是所有平台统一的 Codex 状态根目录(配置、认证、日志、会话均在此),默认 `~/.codex`。本脚本与官方行为完全一致。

**自动化能力一览:**

| 能力 | 机制 | 说明 |
| --- | --- | --- |
| 自动刷新模型 | 定时任务每小时运行一次 + 登录时运行(macOS) | 官方缓存更新后 1 小时内自动同步可见目录 |
| 日志自动删除 | 超过 1MB 自动轮转为主日志 `.old`,超过 7 天的旧日志自动删除 | 日志位于 `<CODEX_ROOT>/log/auto-model-cache.log`,不占磁盘 |
| 无变化零操作 | 内容比对后跳过写入,不产生无用 IO | 幂等设计,重复运行无副作用 |
| 新增隐藏模型自动可见 | 不硬编码模型名,所有 `hide` 自动改 `list` | 未来任何新隐藏模型(不管叫什么)自动生效 |

**手动运行:**

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/auto-model-cache.py"
```

**Windows:**

```powershell
$CodexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
python "$CodexRoot\auto-model-cache.py"
```

**定时任务(三平台):**

- **macOS**:一键安装自动注册 launchd(每小时,登录时运行);也可手动:

```bash
CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
sed "s|__CODEX_ROOT__|$CODEX_ROOT|g" launchd/com.ck.auto-model-cache.plist > ~/Library/LaunchAgents/com.ck.auto-model-cache.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ck.auto-model-cache.plist
```

> 手动方式不做 XML 转义,路径含 `&` `<` `>` `|` 等特殊字符时请改用一键安装。

- **Linux**:一键安装自动注册 crontab;也可手动:

```bash
CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
PYTHON_BIN="$(command -v python3 || echo /usr/bin/python3)"
crontab -l > /tmp/cron.bak
grep -v "auto-model-cache.py" /tmp/cron.bak | crontab -
echo "0 * * * * $PYTHON_BIN \"$CODEX_ROOT/auto-model-cache.py\" \"$CODEX_ROOT\"" | crontab -
crontab -l | grep auto-model-cache
```

- **Windows**:一键安装自动注册计划任务;也可手动(管理员 PowerShell):

```powershell
$CodexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$Action = New-ScheduledTaskAction -Execute 'python' -Argument "`"$CodexRoot\auto-model-cache.py`" `"$CodexRoot`""
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'CodexAutoModelCache' -Action $Action -Trigger $Trigger -Settings $Settings -Force
```

查看任务:`Get-ScheduledTask -TaskName 'CodexAutoModelCache'`。

**卸载定时任务:**

- macOS:`launchctl bootout gui/$(id -u)/com.ck.auto-model-cache`
- Linux:`crontab -l | grep -v "auto-model-cache.py" | crontab -`
- Windows:`Unregister-ScheduledTask -TaskName 'CodexAutoModelCache'`

## 为什么不消耗额度

根据社区观察:

1. 隐藏路由模型不是公开 API 模型:`supported_in_api: false` 意味着不走 API 计费通道
2. 它是内部路由别名:可能指向与公开模型相同的权重,但走了不同的计费路径
3. 消费明细中不出现:连续使用一周,OpenAI 账单页面完全没有对应的用量记录
4. 不影响正常额度:使用后,正常的 5 小时 / 1 周用量窗口不受影响

> 推测:这类模型可能是 OpenAI 内部测试或特殊用途的路由别名,被意外包含在下发给所有客户端的模型目录中。

## 常见问题 FAQ

### Q1: 会不会被封号?

目前没有任何案例。没有修改任何认证信息,没有伪造任何请求,只是在本地目录中把一个已有条目从隐藏改成可见,属于合法的客户端配置行为。但 OpenAI 随时可能在服务器端关闭这个路由,能用就多用。

### Q2: 为什么不直接改 models_cache.json?

因为 Codex 会自动刷新覆盖这个文件。用独立的 `models_auto_visible.json` 更安全,不会被覆盖,也方便回滚。

### Q3: 客户端升级后怎么办?

新版本可能改变模型目录的字段结构。升级后需要从新的 `models_cache.json` 重新生成自定义目录,不能一直用旧版的 JSON。本项目的自动同步脚本已自动处理。

### Q4: 可以复制别人的 auth/token 吗?

绝对不要。复制认证信息既不能可靠获得模型权限(权限绑定在账号上),还会带来账号安全风险。

### Q5: Free 账号有没有办法绕过?

目前没有。服务器的权限判断和本地目录是两层独立逻辑,改本地目录无法补出权限。

### Q6: codex-auto-review 是什么?

模型目录里的另一个隐藏条目,用于 Codex 内部的代码审核功能。本项目默认将其一并显示,无需专门调用;如只想暴露指定 slug,参见"严格模式"。

### Q7: Windows 中文系统乱码怎么办?

所有脚本与示例命令均已显式使用 UTF-8 读写文件。若 PowerShell 控制台仍显示乱码,先执行 `chcp 65001` 再运行。

### Q8: 严格模式(只暴露指定模型,不显示 auto-review)?

默认同步脚本会把所有隐藏模型改为可见。如需只暴露某个 slug,替换脚本中"隐藏→可见"循环为(把 slug 换成你的):

```python
VISIBLE_OVERRIDES = {"gpt-5.6-sol-wm"}
changed = []
for m in visible["models"]:
    if m.get("slug") in VISIBLE_OVERRIDES and m.get("visibility") == "hide":
        m["visibility"] = "list"
        changed.append(m.get("slug"))
```

## 回滚方法

> 回滚 = 删除第 5 步添加的 `model_catalog_json` 一行即可,原有的 `model` 默认值不受影响(未曾改动)。如第 5 步前备份过 config.toml,也可直接恢复备份:

**Windows:**

```powershell
$CodexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
# 恢复到最新备份(如之前备份过)
$Backup = Get-ChildItem -Path $CodexRoot -Filter 'config.toml.before-hidden-*.bak' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($Backup) { Copy-Item -LiteralPath $Backup.FullName -Destination (Join-Path $CodexRoot 'config.toml') -Force }
# 删除自定义目录与定时任务
Remove-Item -LiteralPath (Join-Path $CodexRoot 'models_auto_visible.json') -Force -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName 'CodexAutoModelCache' -Confirm:$false -ErrorAction SilentlyContinue
```

**macOS / Linux:**

```bash
CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
# 恢复到最新备份(如之前备份过)
BACKUP=$(ls -t "$CODEX_ROOT"/config.toml.before-hidden-*.bak 2>/dev/null | head -1)
if [ -n "$BACKUP" ]; then cp "$BACKUP" "$CODEX_ROOT/config.toml"; fi
# 删除自定义目录与定时任务
rm -f "$CODEX_ROOT/models_auto_visible.json"
launchctl bootout "gui/$(id -u)/com.ck.auto-model-cache" 2>/dev/null || true   # macOS
crontab -l | grep -v "auto-model-cache.py" | crontab -                         # Linux
```

最后:彻底退出 Codex → 重启 Codex,即恢复原样。

> 提示:第 3 步生成的 `models_cache.before-hidden-*.bak` 缓存备份可一并删除(可选,保留更安全)。

## 支持与赞赏

如果这个教程对你有帮助,欢迎支持:

| 方式 | 联系方式 |
| --- | --- |
| 微信 | 1837620622(传康Kk) |
| 邮箱 | 2040168455@qq.com |
| 咸鱼 / B站 | 万能程序员 |

## 目录结构

```
codex-hidden-model-guide/
├── README.md                      # 本教程
├── install.sh                     # macOS / Linux 一键安装(自动识别路径 + launchd / cron 定时)
├── install.ps1                    # Windows 一键安装(自动识别路径 + 计划任务)
├── scripts/
│   └── auto-model-cache.py        # 自动同步脚本(跨平台,每小时)
└── launchd/
    └── com.ck.auto-model-cache.plist  # macOS launchd 模板(占位符 __CODEX_ROOT__)
```

---

> 免责声明:本教程仅用于技术研究与学习。本操作本质是修改客户端本地展示配置(把服务器已下发的隐藏条目改为可见),是否违反服务条款由 OpenAI 官方认定,存在账号风险,后果自负;隐藏模型机制依赖官方服务端行为,官方可能随时修复;使用第三方充值站同样存在封号风险,请自行评估。
