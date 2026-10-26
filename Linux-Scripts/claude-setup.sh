#!/usr/bin/env bash
# ============================================================
# claude-setup.sh — Claude Code 一键安装配置工具（交互式菜单版）
#
# 支持平台：智谱 GLM / Kimi / DeepSeek / Anthropic 官方 /
#           第三方中转站（PackyCode、88code、AiHubMix 等）/ 自定义
#
# 子命令：
#   （无参数）  全流程：安装环境 → 选平台 → 配置 → 验证
#   install     仅安装环境（Node.js + Claude Code + 全局命令）
#   config      仅配置接入平台（菜单选择 + 输入 Key）
#   show        查看当前配置（Token 自动打码）
#   doctor      诊断：版本 + API 连通性测试
#   help        显示本帮助
#
# 免交互模式（适合脚本调用）：
#   claude-setup.sh config --base-url https://xxx --token sk-xxx --yes
#
# 通用选项：
#   --base-url <URL>   指定 API 地址（跳过平台菜单）
#   --token <KEY>      指定 API Key（跳过输入）
#   --model <名称>     指定默认模型
#   --timeout <秒>     API 超时秒数（默认 600）
#   --perm <模式>      权限模式: default|acceptEdits|plan|bypassPermissions
#   -y, --yes          免确认，未指定的项全部用默认值
# ============================================================
set -euo pipefail

# ---------- 常量 ----------
NODE_VERSION="v20.18.1"
NODE_MIRROR="https://cdn.npmmirror.com/binaries/node"
NPM_REGISTRY="https://registry.npmmirror.com"
NODE_DIR="$HOME/.local/share/nodejs"
CLAUDE_DIR="$HOME/.claude"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

# 平台预设（名称 / API地址 / 可选模型(|分隔) / 后台小模型，空=不设置）
P_DESC=(
  "智谱 GLM（bigmodel.cn · 官方 Claude 协议接入）"
  "Kimi 月之暗面（moonshot.cn · 官方 Claude 协议接入）"
  "DeepSeek（api.deepseek.com · 官方 Claude 协议接入）"
  "Anthropic 官方（需海外网络环境）"
  "第三方中转站（PackyCode / 88code / AiHubMix 等）"
  "完全自定义（手动输入地址与模型）"
)
P_URL=(
  "https://open.bigmodel.cn/api/anthropic"
  "https://api.moonshot.cn/anthropic"
  "https://api.deepseek.com/anthropic"
  "https://api.anthropic.com"
  ""
  ""
)
P_MODELS=(
  "glm-5.3-flash|glm-4.6|glm-4.5|glm-4.5-air"
  "kimi-k2-turbo-preview|kimi-k2-0905-preview"
  "deepseek-chat|deepseek-reasoner"
  "claude-sonnet-4-5|claude-opus-4-5|claude-haiku-4-5"
  "claude-sonnet-4-5|claude-opus-4-5|claude-haiku-4-5"
  ""
)
P_SMALL=(
  "glm-5.3-flash"
  "kimi-k2-turbo-preview"
  "deepseek-chat"
  ""
  "claude-haiku-4-5"
  ""
)

# ---------- 输出工具 ----------
log()  { echo -e "\033[32m[完成]\033[0m $*"; }
info() { echo -e "\033[36m[信息]\033[0m $*"; }
warn() { echo -e "\033[33m[警告]\033[0m $*"; }
err()  { echo -e "\033[31m[失败]\033[0m $*"; }
die()  { err "$*"; exit 1; }

# ---------- 菜单工具：显示编号选项，返回所选序号 ----------
menu_idx() {
  local title="$1"; shift
  local n=$# i=1 sel
  {
    echo
    info "$title"
    for opt in "$@"; do echo "   $i) $opt"; i=$((i+1)); done
  } >&2
  while true; do
    read -r -p "请选择 [1-$n]（回车=1）: " sel
    [[ -z "$sel" ]] && sel=1
    if [[ "$sel" =~ ^[0-9]+$ ]] && (( sel>=1 && sel<=n )); then echo "$sel"; return; fi
    warn "无效输入: $sel" >&2
  done
}

mask_token() { [[ ${#1} -gt 12 ]] && echo "${1:0:6}****${1: -4}" || echo "****"; }

# ---------- 帮助 ----------
show_help() { awk 'NR==1{next} /^#|^$/{print; next} {exit}' "$0" | sed 's/^#\{0,1\} \{0,1\}//'; }

# ============================================================
# 安装部分（幂等，已装自动跳过）
# ============================================================
step_node() {
  if [[ -x "$NODE_DIR/bin/node" ]] && "$NODE_DIR/bin/node" -v &>/dev/null; then
    log "Node.js 已安装: $("$NODE_DIR/bin/node" -v)"
  elif command -v node &>/dev/null && [[ "$(node -v | cut -c2- | cut -d. -f1)" -ge 18 ]]; then
    log "系统已有 Node.js: $(node -v)"
  else
    info "安装 Node.js $NODE_VERSION 到用户目录（国内镜像）..."
    case "$(uname -m)" in
      x86_64)  node_arch="x64" ;;
      aarch64) node_arch="arm64" ;;
      *) die "不支持的架构: $(uname -m)" ;;
    esac
    tarball="node-${NODE_VERSION}-linux-${node_arch}.tar.xz"
    curl -fSL --retry 3 -o /tmp/claude-node.tar.xz "${NODE_MIRROR}/${NODE_VERSION}/${tarball}" \
      || die "Node.js 下载失败，请检查网络"
    mkdir -p "$NODE_DIR"
    tar -xJf /tmp/claude-node.tar.xz -C "$NODE_DIR" --strip-components=1
    rm -f /tmp/claude-node.tar.xz
    log "Node.js 安装完成: $("$NODE_DIR/bin/node" -v)"
  fi
  export PATH="$NODE_DIR/bin:$PATH"
}

step_claude() {
  if command -v claude &>/dev/null && claude --version &>/dev/null; then
    log "Claude Code 已安装: $(claude --version)"
  else
    info "通过 npm 镜像源安装 Claude Code..."
    npm config set registry "$NPM_REGISTRY"
    npm install -g @anthropic-ai/claude-code || die "npm 安装失败，请检查网络后重试"
    log "Claude Code 安装完成: $(claude --version)"
  fi
}

step_link() {
  if command -v claude &>/dev/null && [[ "$(command -v claude)" != "$NODE_DIR"* ]]; then
    log "claude 已在全局 PATH: $(command -v claude)"
  elif sudo -n ln -sf "$NODE_DIR/bin/claude" "$NODE_DIR/bin/node" \
        "$NODE_DIR/bin/npm" "$NODE_DIR/bin/npx" /usr/local/bin/ 2>/dev/null; then
    log "已软链接到 /usr/local/bin（开机即用）"
  elif [[ $ASSUME_YES -eq 1 ]]; then
    _write_path_rc
  else
    info "需要 sudo 把命令链接到 /usr/local/bin（开机即用）"
    if sudo ln -sf "$NODE_DIR/bin/claude" "$NODE_DIR/bin/node" \
         "$NODE_DIR/bin/npm" "$NODE_DIR/bin/npx" /usr/local/bin/; then
      log "已软链接到 /usr/local/bin"
    else
      warn "sudo 失败，改用 PATH 方式"
      _write_path_rc
    fi
  fi
}
_write_path_rc() {
  grep -qs 'nodejs/bin' ~/.bashrc || echo "export PATH=$NODE_DIR/bin:\$PATH" >> ~/.bashrc
  grep -qs 'nodejs/bin' ~/.profile || echo "export PATH=$NODE_DIR/bin:\$PATH" >> ~/.profile
  log "已写入 ~/.bashrc 和 ~/.profile（重新登录终端生效）"
}

# ============================================================
# 配置部分
# ============================================================
do_config() {
  local BASE_URL="$CFG_URL" TOKEN="$CFG_TOKEN" MODEL="$CFG_MODEL"
  local TIMEOUT_MS="${CFG_TIMEOUT}000" PERM="$CFG_PERM" SMALL="" THEME_SKIP=1

  # ---- 平台 / 地址 / 模型（菜单选择）----
  if [[ -z "$BASE_URL" ]]; then
    local pidx; pidx=$(menu_idx "① 选择接入平台" "${P_DESC[@]}")
    case $pidx in
      5|6) read -r -p "请输入 API 地址 (https://...): " BASE_URL; [[ -z "$BASE_URL" ]] && die "地址不能为空" ;;
      *)   BASE_URL="${P_URL[$((pidx-1))]}" ;;
    esac
    BASE_URL="${BASE_URL%/}"

    # 模型菜单（官方/中转/自定义平台才出现"自定义"项）
    local -a model_opts=()
    [[ -n "${P_MODELS[$((pidx-1))]}" ]] && IFS='|' read -ra model_opts <<< "${P_MODELS[$((pidx-1))]}"
    local midx; midx=$(menu_idx "② 选择默认模型" "${model_opts[@]}" "自定义模型名")
    if (( midx <= ${#model_opts[@]} )); then
      MODEL="${model_opts[$((midx-1))]}"
    else
      read -r -p "请输入模型名: " MODEL; [[ -z "$MODEL" ]] && MODEL=""
    fi
    SMALL="${P_SMALL[$((pidx-1))]}"
  fi

  # ---- API Key（输入方式，不回显）----
  if [[ -z "$TOKEN" ]]; then
    local old_token; old_token=$(get_cfg_val ANTHROPIC_AUTH_TOKEN || true)
    [[ -n "$old_token" ]] && info "当前已配置 Key: $(mask_token "$old_token")（直接回车保留）"
    read -r -s -p "请输入 API Key (sk-...): " TOKEN; echo
    [[ -z "$TOKEN" ]] && TOKEN="$old_token"
    [[ -z "$TOKEN" ]] && die "未提供 API Key，中止"
  fi

  # ---- 超时（菜单选择；--yes 模式默认 10 分钟）----
  if [[ $ASSUME_YES -eq 1 ]]; then
    [[ -n "$CFG_TIMEOUT" ]] && TIMEOUT_MS=$((CFG_TIMEOUT*1000)) || TIMEOUT_MS=600000
  elif [[ -n "$CFG_TIMEOUT" ]]; then
    TIMEOUT_MS=$((CFG_TIMEOUT*1000))
  else
    case $(menu_idx "③ API 超时时间" "5 分钟" "10 分钟（推荐）" "30 分钟（长任务）") in
      1) TIMEOUT_MS=300000 ;; 2) TIMEOUT_MS=600000 ;; 3) TIMEOUT_MS=1800000 ;;
    esac
  fi

  # ---- 权限模式（菜单选择；--yes 模式默认 default）----
  if [[ $ASSUME_YES -eq 1 ]]; then
    PERM="$CFG_PERM"; [[ "$PERM" == "default" ]] && PERM=""
  elif [[ -z "$PERM" || "$PERM" == "default" ]]; then
    PERM=""
    case $(menu_idx "④ 文件修改权限模式" "default：每次修改都询问（安全）" \
        "acceptEdits：自动接受文件编辑（推荐）" \
        "plan：只做规划不修改" \
        "bypassPermissions：全自动（有风险，慎选）") in
      1) PERM="default" ;; 2) PERM="acceptEdits" ;; 3) PERM="plan" ;; 4) PERM="bypassPermissions" ;;
    esac
  fi
  [[ "$PERM" == "default" ]] && PERM=""

  # ---- 主题（菜单选择）----
  if [[ $ASSUME_YES -eq 0 ]]; then
    case $(menu_idx "⑤ 界面主题" "深色 dark" "浅色 light" "跳过，不修改") in
      1) THEME="dark";  THEME_SKIP=0 ;; 2) THEME="light"; THEME_SKIP=0 ;;
    esac
  fi

  # ---- 写入 settings.json ----
  BASE_URL="${BASE_URL%/}"
  mkdir -p "$CLAUDE_DIR"
  [[ -f "$SETTINGS_FILE" ]] && cp "$SETTINGS_FILE" "${SETTINGS_FILE}.bak.$(date +%s)"

  local env_json="" first=1
  _add() { if (( first )); then env_json="    \"$1\": \"$2\""; first=0; else env_json+=",\n    \"$1\": \"$2\""; fi; }
  _add "ANTHROPIC_BASE_URL" "$BASE_URL"
  _add "ANTHROPIC_AUTH_TOKEN" "$TOKEN"
  [[ -n "$MODEL" ]] && _add "ANTHROPIC_MODEL" "$MODEL"
  [[ -n "$SMALL" ]] && _add "ANTHROPIC_SMALL_FAST_MODEL" "$SMALL"
  _add "API_TIMEOUT_MS" "$TIMEOUT_MS"

  local perm_json=""
  [[ -n "$PERM" ]] && perm_json=',\n  "permissions": {\n    "defaultMode": "'"$PERM"'"\n  }'

  printf '{\n  "env": {\n%b\n  }%b\n}\n' "$env_json" "$perm_json" > "$SETTINGS_FILE"
  chmod 600 "$SETTINGS_FILE"
  log "配置已写入 $SETTINGS_FILE（旧文件已备份，权限 600）"

  if (( THEME_SKIP == 0 )) && command -v claude &>/dev/null; then
    claude config set --global theme "$THEME" >/dev/null 2>&1 && log "主题已设为 $THEME"
  fi

  # ---- 配置摘要 ----
  echo
  info "========== 配置摘要 =========="
  echo "   API 地址 : $BASE_URL"
  echo "   API Key  : $(mask_token "$TOKEN")"
  [[ -n "$MODEL" ]] && echo "   默认模型 : $MODEL"
  [[ -n "$SMALL" ]] && echo "   后台模型 : $SMALL"
  echo "   超时时间 : $((TIMEOUT_MS/1000)) 秒"
  [[ -n "$PERM" ]] && echo "   权限模式 : $PERM"
  echo "=============================="
}

# ============================================================
# 验证 / 诊断
# ============================================================
probe_api() {  # $1=url $2=token → 设置全局 CODE BODY
  CODE=$(curl -s -o /tmp/claude-probe.json -w "%{http_code}" --max-time 15 \
    -X POST "$1/v1/messages" \
    -H "content-type: application/json" -H "x-api-key: $2" \
    -H "anthropic-version: 2023-06-01" \
    -d '{"model":"claude-sonnet-4-5","max_tokens":1,"messages":[{"role":"user","content":"hi"}]}' || true)
  BODY="$(cat /tmp/claude-probe.json 2>/dev/null || true)"
  rm -f /tmp/claude-probe.json
}

do_verify() {
  local url="$1" token="$2"
  info "验证连通性: $url ..."
  probe_api "$url" "$token"
  case "$CODE" in
    200) log "API 连通正常，认证成功！可以直接使用 claude 了" ;;
    401|403)
      if [[ "$BODY" == *"Request not allowed"* || "$BODY" == *"unavailable-in-region"* ]]; then
        err "该接口在你所在区域被封锁 (HTTP $CODE)"; die "官方直连需要海外网络/代理，建议改用方案①②③或中转站"
      fi
      err "认证被拒绝 (HTTP $CODE)，请检查 API Key 是否正确/有余额"; die "响应: ${BODY:-(无响应体)}" ;;
    404) warn "地址可达但接口 404，请确认填的是 API 地址而非网页地址" ;;
    000) err "无法连接 $url，请检查地址和网络"; die "若地址确认无误，可能是平台暂时不可用" ;;
    *)   warn "HTTP $CODE（非标准响应），建议运行 claude 实测: ${BODY:-(无响应体)}" ;;
  esac
}

get_cfg_val() {  # $1=key → 打印 settings.json 中对应值
  [[ -f "$SETTINGS_FILE" ]] || return 1
  grep -o "\"$1\"[^,}]*" "$SETTINGS_FILE" | head -1 | cut -d'"' -f4
}

do_show() {
  [[ -f "$SETTINGS_FILE" ]] || { warn "尚未配置，请先运行: $0 config"; return 0; }
  info "当前配置 ($SETTINGS_FILE):"
  local t; t=$(get_cfg_val ANTHROPIC_AUTH_TOKEN || true)
  sed 's/"ANTHROPIC_AUTH_TOKEN":.*/"ANTHROPIC_AUTH_TOKEN": "'"$(mask_token "$t")"'（已打码）",/' "$SETTINGS_FILE"
}

do_doctor() {
  info "===== Claude Code 诊断 ====="
  command -v claude &>/dev/null && log "claude 命令: $(command -v claude) ($(claude --version 2>/dev/null || echo '?'))" \
    || err "claude 命令未找到，请先运行: $0 install"
  command -v node &>/dev/null && log "node: $(node -v)" || warn "node 不在 PATH"
  [[ -f "$SETTINGS_FILE" ]] || { warn "尚未配置 API，请先运行: $0 config"; return 0; }
  local url t; url=$(get_cfg_val ANTHROPIC_BASE_URL || true); t=$(get_cfg_val ANTHROPIC_AUTH_TOKEN || true)
  [[ -z "$url" || -z "$t" ]] && { warn "配置不完整"; return 0; }
  do_verify "$url" "$t"
}

# ============================================================
# 参数解析与入口
# ============================================================
CFG_URL="" CFG_TOKEN="" CFG_MODEL="" CFG_TIMEOUT="" CFG_PERM="" ASSUME_YES=0
CMD="full"
while [[ $# -gt 0 ]]; do
  case "$1" in
    install)        CMD="install"; shift ;;
    config)         CMD="config";  shift ;;
    show)           CMD="show";    shift ;;
    doctor)         CMD="doctor";  shift ;;
    help|-h|--help) show_help; exit 0 ;;
    --base-url)     CFG_URL="$2"; shift 2 ;;
    --token)        CFG_TOKEN="$2"; shift 2 ;;
    --model)        CFG_MODEL="$2"; shift 2 ;;
    --timeout)      CFG_TIMEOUT="$2"; shift 2 ;;
    --perm)         CFG_PERM="$2"; shift 2 ;;
    -y|--yes)       ASSUME_YES=1; shift ;;
    *)              err "未知参数: $1"; show_help; exit 1 ;;
  esac
done

case "$CMD" in
  show)    do_show ;;
  doctor)  do_doctor ;;
  install) step_node; step_claude; step_link ;;
  config)  do_config; [[ -n "$CFG_URL" && $ASSUME_YES -eq 1 ]] && do_verify "${CFG_URL%/}" "$CFG_TOKEN" ;;
  full)
    step_node; step_claude; step_link
    do_config
    URL=$(get_cfg_val ANTHROPIC_BASE_URL); TOKEN=$(get_cfg_val ANTHROPIC_AUTH_TOKEN)
    do_verify "$URL" "$TOKEN"
    echo; log "全部完成！进入项目目录运行 claude 即可开始使用"
    ;;
esac
