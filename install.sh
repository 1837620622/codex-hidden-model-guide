#!/usr/bin/env bash
# Codex 隐藏模型自动同步脚本安装器(macOS)
# 自动识别 CODEX_ROOT(命令行参数 > CODEX_HOME > ~/.codex),安装脚本、生成可见目录、注册 launchd 定时任务
set -euo pipefail

# ---- 自动识别 Codex 根目录 ----
CODEX_ROOT="${1:-${CODEX_HOME:-$HOME/.codex}}"
CODEX_ROOT="${CODEX_ROOT%/}"  # 去除尾部斜杠,保证路径一致

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_SRC="$SCRIPT_DIR/scripts/auto-model-cache.py"
PLIST_SRC="$SCRIPT_DIR/launchd/com.ck.auto-model-cache.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.ck.auto-model-cache.plist"
LABEL="com.ck.auto-model-cache"

echo "==> Codex 根目录: $CODEX_ROOT"

# ---- 1. 检查缓存是否存在 ----
if [ ! -f "$CODEX_ROOT/models_cache.json" ]; then
    echo "错误: 未找到 $CODEX_ROOT/models_cache.json" >&2
    echo "请先正常使用一次 Codex 生成缓存后重试" >&2
    exit 1
fi

# ---- 2. 安装同步脚本 ----
mkdir -p "$CODEX_ROOT"
cp "$SCRIPT_SRC" "$CODEX_ROOT/auto-model-cache.py"
chmod +x "$CODEX_ROOT/auto-model-cache.py"
echo "==> 已安装脚本: $CODEX_ROOT/auto-model-cache.py"

# ---- 3. 首次运行,生成可见模型目录 ----
/usr/bin/python3 "$CODEX_ROOT/auto-model-cache.py" "$CODEX_ROOT"
echo "==> 已生成可见目录: $CODEX_ROOT/models_auto_visible.json"

# ---- 4. 生成 launchd 配置(占位符替换) ----
mkdir -p "$HOME/Library/LaunchAgents" "$CODEX_ROOT/log"
# 转义分两步,顺序关键:
#   第一步:先把路径中的 & < > 替换为 XML 实体(此时路径中不再有原始 &)
#   第二步:再把路径中剩余的 sed 特殊字符(替换串中的 \ | 和实体自身的 &)
#           全部转义为 \\ \| \&,防止 sed 替换时被解释
ESCAPED_ROOT=$(printf '%s' "$CODEX_ROOT" \
  | sed -e 's/&/__AMP__/g' -e 's/</__LT__/g' -e 's/>/__GT__/g' \
  | sed -e 's/\\/\\\\/g' -e 's/|/\\|/g' -e 's/__AMP__/\\\&amp;/g' -e 's/__LT__/\\\&lt;/g' -e 's/__GT__/\\\&gt;/g')
sed "s|__CODEX_ROOT__|$ESCAPED_ROOT|g" "$PLIST_SRC" > "$PLIST_DST"
echo "==> 已写入定时任务配置: $PLIST_DST"

# ---- 5. 注册 launchd(先移除旧任务避免冲突,忽略错误) ----
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
echo "==> 定时任务已注册: $LABEL (每小时运行一次)"

# ---- 6. 提示下一步 ----
echo ""
echo "完成!下一步:在 $CODEX_ROOT/config.toml 顶层添加:"
echo "  model = \"gpt-5.6-sol-wm\""
echo "  model_catalog_json = \"$CODEX_ROOT/models_auto_visible.json\""
echo "然后彻底退出并重启 Codex 即可生效。"
echo ""
echo "验证: /usr/bin/python3 $CODEX_ROOT/auto-model-cache.py $CODEX_ROOT"
echo "日志: $CODEX_ROOT/log/auto-model-cache.log (超过 1MB 自动轮转,超过 7 天自动删除)"