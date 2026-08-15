# Codex 隐藏模型自动同步脚本安装器(Windows PowerShell 5.1+)
# 自动识别 CODEX_ROOT(命令行参数 > CODEX_HOME > %USERPROFILE%\.codex)
# 安装脚本、生成可见目录、注册计划任务(每小时)
# 注意:所有文件读写显式使用 UTF-8,避免中文系统 GBK 默认编码导致乱码
$ErrorActionPreference = 'Stop'

# ---- 控制台输出编码固定为 UTF-8,避免中文提示乱码 ----
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}

# ---- 管理员权限检查(注册计划任务需要) ----
$IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $IsAdmin) {
    Write-Host "错误: 需要以管理员身份运行(注册计划任务需要管理员权限)" -ForegroundColor Red
    Write-Host "请右键 PowerShell -> 以管理员身份运行,然后重试" -ForegroundColor Yellow
    exit 1
}

# ---- 自动识别 Codex 根目录 ----
$CodexRoot = if ($args.Count -gt 0 -and $args[0]) {
    $args[0].TrimEnd('\')
} elseif ($env:CODEX_HOME) {
    $env:CODEX_HOME.TrimEnd('\')
} else {
    Join-Path $env:USERPROFILE '.codex'
}
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptSrc = Join-Path $ScriptDir 'scripts\auto-model-cache.py'
$ScriptDst = Join-Path $CodexRoot 'auto-model-cache.py'

Write-Host "==> Codex 根目录: $CodexRoot"

# ---- 1. 检查缓存是否存在 ----
$CachePath = Join-Path $CodexRoot 'models_cache.json'
if (-not (Test-Path -LiteralPath $CachePath)) {
    Write-Host "错误: 未找到 $CachePath" -ForegroundColor Red
    Write-Host "请先正常使用一次 Codex 生成缓存后重试" -ForegroundColor Yellow
    exit 1
}

# ---- 2. 定位 Python(优先 py launcher,回退 python) ----
$PythonCmd = $null
$pyTest = Get-Command 'py' -ErrorAction SilentlyContinue
if ($pyTest) { $PythonCmd = 'py'; $PyArgs = @('-3') }
else {
    $pyTest = Get-Command 'python' -ErrorAction SilentlyContinue
    if ($pyTest) { $PythonCmd = 'python'; $PyArgs = @() }
}
if (-not $PythonCmd) {
    Write-Host "错误: 未找到 Python,请先安装 https://www.python.org/downloads/ (安装时勾选 Add to PATH)" -ForegroundColor Red
    exit 1
}
Write-Host "==> 使用 Python: $PythonCmd"

# ---- 3. 安装同步脚本 ----
New-Item -ItemType Directory -Path $CodexRoot -Force | Out-Null
Copy-Item -LiteralPath $ScriptSrc -Destination $ScriptDst -Force
Write-Host "==> 已安装脚本: $ScriptDst"

# ---- 4. 首次运行,生成可见模型目录 ----
& $PythonCmd @PyArgs $ScriptDst $CodexRoot
if ($LASTEXITCODE -ne 0) { throw "脚本执行失败,退出码 $LASTEXITCODE" }
$VisibleCatalog = Join-Path $CodexRoot 'models_auto_visible.json'
Write-Host "==> 已生成可见目录: $VisibleCatalog"

# ---- 5. 注册计划任务(每小时运行一次) ----
# 注意:py launcher 需带 -3 参数,确保计划任务使用 Python 3
if ($PythonCmd -eq 'py') {
    $Action = New-ScheduledTaskAction -Execute 'py' -Argument "-3 `"$ScriptDst`" `"$CodexRoot`""
} else {
    $Action = New-ScheduledTaskAction -Execute 'python' -Argument "`"$ScriptDst`" `"$CodexRoot`""
}
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'CodexAutoModelCache' -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null
Write-Host "==> 计划任务已注册: CodexAutoModelCache (每小时运行一次)"

# ---- 6. 提示下一步 ----
Write-Host ""
Write-Host "完成!下一步:在 $CodexRoot\config.toml 顶层添加一行:"
Write-Host "  model_catalog_json = `"$VisibleCatalog`""
Write-Host "然后在 Codex 模型选择器中自主选择隐藏路由模型(如 gpt-5.6-sol-wm)。"
Write-Host "建议不要设为默认模型:隐藏路由模型可能随时失效,失效后可随时切换回正常模型。"
Write-Host ""
if ($PythonCmd -eq 'py') {
    Write-Host "验证: py -3 $ScriptDst $CodexRoot"
} else {
    Write-Host "验证: python $ScriptDst $CodexRoot"
}
Write-Host "日志: $CodexRoot\log\auto-model-cache.log (超过 1MB 自动轮转,超过 7 天自动删除)"