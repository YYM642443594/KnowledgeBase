#!/usr/bin/env bash
# ============================================================
# openclaw-setup.sh — OpenClaw 一键安装配置工具（主菜单版）
#
# OpenClaw（原 Clawdbot/Moltbot）：开源个人 AI 助理网关，
# 可接入 WhatsApp / Telegram / Discord / iMessage 等聊天渠道，
# 由 Claude / GLM / Kimi / DeepSeek 等模型驱动。
#
# 直接运行（无参数）→ 弹出主菜单选择：安装 / 配置 / 查询 / 诊断
#
# 子命令（跳过菜单直接执行）：
#   （无参数）  主菜单
#   full        全流程：安装环境 → 选平台 → 配置 → 验证
#   install     仅安装环境（Node 26 + OpenClaw + 全局命令）
#   config      仅配置模型接入（菜单选择 + 输入 Key）
#   show        查看当前配置（Key 自动打码）
#   doctor      诊断：Node/OpenClaw 版本 + API 连通性
#   help        显示本帮助
#
# 免交互模式（适合脚本调用）：
#   openclaw-setup.sh config --base-url https://xxx --token sk-xxx --yes
#
# 通用选项：
#   --base-url <URL>   指定 API 地址（跳过平台菜单）
#   --token <KEY>      指定 API Key（跳过输入）
#   --model <名称>     指定默认模型
#   -y, --yes          免确认，未指定的项全部用默认值
#
# 注意：OpenClaw 要求 Node >= 24.22.1 或 >= 26.12.1，
#       本脚本安装 Node v26.12.1（先删旧目录再解压，避免 npm 混装损坏；
#       全局包如 claude-code 会被清除并自动重装）。
# ============================================================
set -euo pipefail

# ---------- 常量 ----------
NODE_VERSION="v26.12.1"          # openclaw engines 要求 >=26.12.1
NODE_MIRROR="https://cdn.npmmirror.com/binaries/node"
NPM_REGISTRY="https://registry.npmmirror.com"
NODE_DIR="$HOME/.local/share/nodejs"
OC_DIR="$HOME/.openclaw"
CONFIG_FILE="$OC_DIR/openclaw.json"

# 平台预设（说明 / API地址 / 可选模型(|分隔) / 提供商标识）
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
P_KEY=("zhipu" "kimi" "deepseek" "anthropic" "relay" "custom")

# ---------- 输出工具 ----------
log()  { echo -e "\033[32m[完成]\033[0m $*"; }
info() { echo -e "\033[36m[信息]\033[0m $*"; }
warn() { echo -e "\033[33m[警告]\033[0m $*"; }
err()  { echo -e "\033[31m[失败]\033[0m $*"; }
die()  { err "$*"; exit 1; }

# ---------- 菜单工具：显示走 stderr，结果走 stdout ----------
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

# ---------- 帮助：打印头部注释，遇到第一行代码即停 ----------
show_help() { awk 'NR==1{next} /^#|^$/{print; next} {exit}' "$0" | sed 's/^#\{0,1\} \{0,1\}//'; }

# ============================================================
# 安装部分（幂等，已装自动跳过）
# ============================================================
node_ok() {  # 判断 $1 版本号 (如 v26.12.1) 是否满足 openclaw 要求
  local major minor
  major=$(echo "$1" | cut -c2- | cut -d. -f1)
  minor=$(echo "$1" | cut -c2- | cut -d. -f2)
  (( major > 26 )) || { [[ "$major" == 26 ]] && (( minor >= 12 )); }
}

step_node() {
  local cur=""
  [[ -x "$NODE_DIR/bin/node" ]] && cur="$("$NODE_DIR/bin/node" -v)" || cur="$(node -v 2>/dev/null || true)"
  # npm 健康检查：版本满足但 npm 损坏（如新旧文件混装）时也强制重装
  if [[ -n "$cur" ]] && node_ok "$cur" && "$NODE_DIR/bin/npm" -v &>/dev/null; then
    log "Node.js 已满足要求: $cur (npm $("$NODE_DIR/bin/npm" -v))"
  else
    [[ -n "$cur" ]] && info "Node $cur 版本过低或 npm 异常，重装为 $NODE_VERSION（Claude Code 兼容，全局包稍后自动恢复）..."
    case "$(uname -m)" in
      x86_64)  node_arch="x64" ;;
      aarch64) node_arch="arm64" ;;
      *) die "不支持的架构: $(uname -m)" ;;
    esac
    tarball="node-${NODE_VERSION}-linux-${node_arch}.tar.xz"
    curl -fSL --retry 3 -o /tmp/oc-node.tar.xz "${NODE_MIRROR}/${NODE_VERSION}/${tarball}" \
      || die "Node.js 下载失败，请检查网络"
    # 必须先删除旧目录再解压：新旧版本的 npm 内部文件混合会导致 npm 损坏
    # （全局包如 claude-code 会一并清除，稍后自动重装）
    rm -rf "$NODE_DIR"
    mkdir -p "$NODE_DIR"
    tar -xJf /tmp/oc-node.tar.xz -C "$NODE_DIR" --strip-components=1
    rm -f /tmp/oc-node.tar.xz
    log "Node.js 安装完成: $("$NODE_DIR/bin/node" -v)"
  fi
  export PATH="$NODE_DIR/bin:$PATH"
}

step_openclaw() {
  if command -v openclaw &>/dev/null && openclaw --version &>/dev/null; then
    log "OpenClaw 已安装: $(openclaw --version)"
  else
    info "通过 npm 镜像源安装 OpenClaw（体积较大，请耐心等待）..."
    # 直接通过 --registry 参数指定镜像源，不修改全局 npm 配置
    npm install -g openclaw@latest --registry="$NPM_REGISTRY" \
      || die "npm 安装失败，请检查网络后重试（详细日志见 ~/.npm/_logs/）"
    # openclaw 的 postinstall 会安装内置插件，npm 11 默认拦截，需显式允许
    npm install -g --allow-scripts=@google/genai,esbuild,koffi,protobufjs,openclaw \
      openclaw@latest --registry="$NPM_REGISTRY" \
      || warn "内置插件安装脚本未执行，功能可能不全（不影响基本使用）"
    log "OpenClaw 安装完成: $(openclaw --version)"
  fi
}

_write_path_rc() {
  grep -qs 'nodejs/bin' ~/.bashrc || echo "export PATH=$NODE_DIR/bin:\$PATH" >> ~/.bashrc
  grep -qs 'nodejs/bin' ~/.profile || echo "export PATH=$NODE_DIR/bin:\$PATH" >> ~/.profile
  log "已写入 ~/.bashrc 和 ~/.profile（重新登录终端生效）"
}

step_link() {
  if command -v openclaw &>/dev/null && [[ "$(command -v openclaw)" != "$NODE_DIR"* ]]; then
    log "openclaw 已在全局 PATH: $(command -v openclaw)"
  elif sudo -n ln -sf "$NODE_DIR/bin/openclaw" "$NODE_DIR/bin/node" \
        "$NODE_DIR/bin/npm" "$NODE_DIR/bin/npx" /usr/local/bin/ 2>/dev/null; then
    log "已软链接到 /usr/local/bin（开机即用）"
  elif [[ $ASSUME_YES -eq 1 ]]; then
    _write_path_rc
  else
    info "需要 sudo 把命令链接到 /usr/local/bin（开机即用）"
    if sudo ln -sf "$NODE_DIR/bin/openclaw" "$NODE_DIR/bin/node" \
         "$NODE_DIR/bin/npm" "$NODE_DIR/bin/npx" /usr/local/bin/; then
      log "已软链接到 /usr/local/bin"
    else
      warn "sudo 失败，改用 PATH 方式"
      _write_path_rc
    fi
  fi
}

# ============================================================
# 模型元数据（上下文窗口 / 最大输出）
# ============================================================
model_meta() {  # $1=模型id → 输出 "名称|上下文|最大输出"
  case "$1" in
    glm-5.3-flash)      echo "GLM-5.3 Flash|128000|16384" ;;
    glm-4.6)            echo "GLM-4.6|200000|16384" ;;
    glm-4.5)            echo "GLM-4.5|128000|16384" ;;
    glm-4.5-air)        echo "GLM-4.5-Air|128000|16384" ;;
    kimi-k2-turbo-preview) echo "Kimi K2 Turbo|262144|8192" ;;
    kimi-k2-0905-preview)  echo "Kimi K2 0905|262144|8192" ;;
    deepseek-chat)      echo "DeepSeek Chat|131072|8192" ;;
    deepseek-reasoner)  echo "DeepSeek Reasoner|131072|8192" ;;
    claude-opus-4-5)    echo "Claude Opus 4.5|200000|32000" ;;
    claude-sonnet-4-5)  echo "Claude Sonnet 4.5|200000|64000" ;;
    claude-haiku-4-5)   echo "Claude Haiku 4.5|200000|32000" ;;
    *)                  echo "$1|128000|8192" ;;
  esac
}

# ============================================================
# 配置部分
# ============================================================
do_config() {
  local BASE_URL="$CFG_URL" TOKEN="$CFG_TOKEN" MODEL="$CFG_MODEL"
  local PROVIDER="" MODELS_JSON="" first=1 mid=""

  # ---- 平台 / 地址（菜单选择）----
  if [[ -z "$BASE_URL" ]]; then
    local pidx; pidx=$(menu_idx "① 选择接入平台" "${P_DESC[@]}")
    PROVIDER="${P_KEY[$((pidx-1))]}"
    case $pidx in
      5|6) read -r -p "请输入 API 地址 (https://...): " BASE_URL; [[ -z "$BASE_URL" ]] && die "地址不能为空" ;;
      *)   BASE_URL="${P_URL[$((pidx-1))]}" ;;
    esac

    # 模型菜单
    local -a model_opts=()
    [[ -n "${P_MODELS[$((pidx-1))]}" ]] && IFS='|' read -ra model_opts <<< "${P_MODELS[$((pidx-1))]}"
    local midx; midx=$(menu_idx "② 选择默认模型" "${model_opts[@]}" "自定义模型名")
    if (( midx <= ${#model_opts[@]} )); then
      MODEL="${model_opts[$((midx-1))]}"
    else
      read -r -p "请输入模型名: " MODEL; [[ -z "$MODEL" ]] && MODEL="${model_opts[0]:-}"
    fi
  else
    PROVIDER="custom"
    # 免交互/未指定模型时给一个可用默认值
    [[ -z "$MODEL" && $ASSUME_YES -eq 1 ]] && MODEL="claude-sonnet-4-5"
  fi
  [[ -z "$MODEL" ]] && die "未确定默认模型，中止"

  # ---- API Key（输入方式，不回显）----
  if [[ -z "$TOKEN" ]]; then
    local old_token; old_token=$(get_cfg_val apiKey || true)
    [[ -n "$old_token" ]] && info "当前已配置 Key: $(mask_token "$old_token")（直接回车保留）"
    read -r -s -p "请输入 API Key (sk-...): " TOKEN; echo
    [[ -z "$TOKEN" ]] && TOKEN="$old_token"
    [[ -z "$TOKEN" ]] && die "未提供 API Key，中止"
  fi

  # ---- 已有配置确认 ----
  if [[ -f "$CONFIG_FILE" && $ASSUME_YES -eq 0 ]]; then
    warn "已存在配置 $CONFIG_FILE，继续将覆盖（渠道等设置请先跑 openclaw onboard 再来改模型）"
    read -r -p "是否继续？[y/N]: " yn
    [[ "$yn" =~ ^[Yy]$ ]] || die "已取消"
  fi

  # ---- 生成模型条目（全部平台模型都写入，便于后续切换）----
  local -a all_models=()
  local idx
  for idx in "${!P_KEY[@]}"; do
    [[ "${P_KEY[$idx]}" == "$PROVIDER" ]] && IFS='|' read -ra all_models <<< "${P_MODELS[$idx]}"
  done
  [[ " ${all_models[*]} " != *" $MODEL "* ]] && all_models+=("$MODEL")
  local m mname mctx mtok
  for m in "${all_models[@]}"; do
    IFS='|' read -r mname mctx mtok <<< "$(model_meta "$m")"
    if (( first )); then
      MODELS_JSON="{ \"id\": \"$m\", \"name\": \"$mname\", \"contextWindow\": $mctx, \"maxTokens\": $mtok }"
      first=0
    else
      MODELS_JSON+=",
          { \"id\": \"$m\", \"name\": \"$mname\", \"contextWindow\": $mctx, \"maxTokens\": $mtok }"
    fi
  done

  # ---- 写入 openclaw.json ----
  BASE_URL="${BASE_URL%/}"
  mkdir -p "$OC_DIR"
  [[ -f "$CONFIG_FILE" ]] && cp "$CONFIG_FILE" "${CONFIG_FILE}.bak.$(date +%s)"
  cat > "$CONFIG_FILE" <<EOF
{
  "models": {
    "mode": "merge",
    "providers": {
      "$PROVIDER": {
        "baseUrl": "$BASE_URL",
        "api": "anthropic-messages",
        "apiKey": "$TOKEN",
        "models": [
          $MODELS_JSON
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": { "primary": "$PROVIDER/$MODEL" }
    }
  },
  "gateway": { "mode": "local" }
}
EOF
  chmod 600 "$CONFIG_FILE"
  log "配置已写入 $CONFIG_FILE（旧文件已备份，权限 600）"

  # ---- 配置摘要 ----
  echo
  info "========== 配置摘要 =========="
  echo "   提供商   : $PROVIDER"
  echo "   API 地址 : $BASE_URL"
  echo "   API Key  : $(mask_token "$TOKEN")"
  echo "   默认模型 : $PROVIDER/$MODEL"
  echo "=============================="
}

# ============================================================
# 验证 / 诊断
# ============================================================
probe_api() {  # $1=url $2=token → 设置全局 CODE BODY
  CODE=$(curl -s -o /tmp/oc-probe.json -w "%{http_code}" --max-time 15 \
    -X POST "$1/v1/messages" \
    -H "content-type: application/json" -H "x-api-key: $2" \
    -H "anthropic-version: 2023-06-01" \
    -d '{"model":"claude-sonnet-4-5","max_tokens":1,"messages":[{"role":"user","content":"hi"}]}' || true)
  BODY="$(cat /tmp/oc-probe.json 2>/dev/null || true)"
  rm -f /tmp/oc-probe.json
}

do_verify() {
  local url="$1" token="$2"
  info "验证连通性: $url ..."
  probe_api "$url" "$token"
  case "$CODE" in
    200) log "API 连通正常，认证成功！" ;;
    401|403)
      if [[ "$BODY" == *"Request not allowed"* || "$BODY" == *"unavailable-in-region"* ]]; then
        err "该接口在你所在区域被封锁 (HTTP $CODE)"; die "官方直连需要海外网络/代理，建议改用智谱/Kimi/DeepSeek 或中转站"
      fi
      err "认证被拒绝 (HTTP $CODE)，请检查 API Key 是否正确/有余额"; die "响应: ${BODY:-(无响应体)}" ;;
    404) warn "地址可达但接口 404，请确认填的是 API 地址而非网页地址" ;;
    000) err "无法连接 $url，请检查地址和网络"; die "若地址确认无误，可能是平台暂时不可用" ;;
    *)   warn "HTTP $CODE（非标准响应），建议运行 openclaw 实测: ${BODY:-(无响应体)}" ;;
  esac
}

get_cfg_val() {  # $1=json键名 → 打印第一个匹配值
  [[ -f "$CONFIG_FILE" ]] || return 1
  grep -o "\"$1\"[^,}]*" "$CONFIG_FILE" | head -1 | cut -d'"' -f4
}

do_show() {
  [[ -f "$CONFIG_FILE" ]] || { warn "尚未配置，请先运行: $0 config"; return 0; }
  info "当前配置 ($CONFIG_FILE):"
  local t; t=$(get_cfg_val apiKey || true)
  sed "s/\"apiKey\":.*/\"apiKey\": \"$(mask_token "$t")\"（已打码）,/" "$CONFIG_FILE"
}

do_doctor() {
  info "===== OpenClaw 诊断 ====="
  local nv; nv="$(node -v 2>/dev/null || true)"
  if [[ -n "$nv" ]] && node_ok "$nv"; then
    log "node: $nv（满足 openclaw 要求）"
  else
    err "node 版本不满足（当前: ${nv:-未安装}，需要 >= 26.12.1），请运行: $0 install"
  fi
  command -v openclaw &>/dev/null && log "openclaw: $(command -v openclaw) ($(openclaw --version 2>/dev/null || echo '?'))" \
    || err "openclaw 命令未找到，请先运行: $0 install"
  [[ -f "$CONFIG_FILE" ]] || { warn "尚未配置模型，请先运行: $0 config"; return 0; }
  local url t; url=$(get_cfg_val baseUrl || true); t=$(get_cfg_val apiKey || true)
  [[ -z "$url" || -z "$t" ]] && { warn "配置不完整"; return 0; }
  do_verify "$url" "$t"
}

# ============================================================
# 主菜单（无参数运行时进入）
# ============================================================
final_tips() {
  echo; log "全部完成！接下来："
  echo "    openclaw onboard    # 交互引导：选模型、连接聊天渠道（WhatsApp/TG等）"
  echo "    openclaw gateway    # 启动网关常驻服务（控制台地址与密钥由此产生）"
  echo "    openclaw doctor     # 内置健康检查"
}

show_menu() {
  local c
  echo -e "\033[35m============================================\033[0m"
  echo -e "\033[35m   OpenClaw 一键安装配置工具\033[0m"
  echo -e "\033[35m============================================\033[0m"
  c=$(menu_idx "请选择要执行的操作" \
    "全自动：安装环境 + 配置模型 + 验证（首次使用推荐）" \
    "仅安装环境（Node / OpenClaw / 全局命令）" \
    "仅配置模型接入（选平台 → 选模型 → 输 Key）" \
    "查询当前配置（Key 自动打码）" \
    "诊断检查（Node/OpenClaw 版本 + API 连通实测）" \
    "显示帮助") || exit 0
  case $c in
    1)
      step_node; step_openclaw; step_link
      do_config
      local url tok; url=$(get_cfg_val baseUrl || true); tok=$(get_cfg_val apiKey || true)
      [[ -n "$url" && -n "$tok" ]] && do_verify "$url" "$tok"
      final_tips
      ;;
    2) step_node; step_openclaw; step_link ;;
    3)
      do_config
      local url tok; url=$(get_cfg_val baseUrl || true); tok=$(get_cfg_val apiKey || true)
      [[ -n "$url" && -n "$tok" ]] && do_verify "$url" "$tok"
      final_tips
      ;;
    4) do_show ;;
    5) do_doctor ;;
    6) show_help ;;
  esac
}

# ============================================================
# 参数解析与入口
# ============================================================
CFG_URL="" CFG_TOKEN="" CFG_MODEL="" ASSUME_YES=0
CMD="" HAS_ARGS=0
while [[ $# -gt 0 ]]; do
  HAS_ARGS=1
  case "$1" in
    full)           CMD="full";     shift ;;
    install)        CMD="install";  shift ;;
    config)         CMD="config";   shift ;;
    show)           CMD="show";     shift ;;
    doctor)         CMD="doctor";   shift ;;
    help|-h|--help) show_help; exit 0 ;;
    --base-url)     CFG_URL="$2"; shift 2 ;;
    --token)        CFG_TOKEN="$2"; shift 2 ;;
    --model)        CFG_MODEL="$2"; shift 2 ;;
    -y|--yes)       ASSUME_YES=1; shift ;;
    *)              err "未知参数: $1"; show_help; exit 1 ;;
  esac
done
# 无任何参数 → 主菜单；有参数但未指定子命令 → 原全流程
[[ -z "$CMD" ]] && { (( HAS_ARGS )) && CMD="full" || CMD="menu"; }

case "$CMD" in
  menu)    show_menu ;;
  show)    do_show ;;
  doctor)  do_doctor ;;
  install) step_node; step_openclaw; step_link ;;
  config)  do_config; [[ -n "$CFG_URL" && $ASSUME_YES -eq 1 ]] && do_verify "${CFG_URL%/}" "$CFG_TOKEN" ;;
  full)
    step_node; step_openclaw; step_link
    do_config
    URL=$(get_cfg_val baseUrl); TOKEN=$(get_cfg_val apiKey)
    do_verify "$URL" "$TOKEN"
    final_tips
    ;;
esac
