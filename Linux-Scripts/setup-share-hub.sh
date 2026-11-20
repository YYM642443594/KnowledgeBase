#!/usr/bin/env bash
# setup-share-hub.sh — share-hub 公网下载站一键部署（YYM 常用机）
#
# 从本仓库 Linux-Scripts/ 目录内随附的 share-hub.py / share-hub.service 出发，
# 自动完成：Tailscale 安装登录 → Funnel 授权 → 文件放置与路径适配 →
# 配置生成 → systemd 用户服务 → Linger → Funnel 映射 → 健康验证。
# 幂等：重复运行只补缺失步骤，不破坏已有配置。
#
# 用法见底部 usage() 或 bash setup-share-hub.sh --help
# 详细说明与手动等价步骤：同目录 share-hub公网下载站部署与运维.md 第 10 节
set -euo pipefail

# ---------- 默认值 ----------
SCAN_ROOT="/mnt/sda1/00.FTP"        # 数据盘根（代码内 SCAN_ROOT 常量）
TMP_DIR="/mnt/sda1/share-hub-tmp"   # zip 临时目录（代码内 TMP_DIR 常量）
PORT=8080                           # 服务端口
SHARE_DIR=""                        # 可选：首条分享链接指向的目录
ASSUME_YES=0
SKIP_SUDO=0

usage() {
    cat <<'EOF'
用法: bash setup-share-hub.sh [选项]

选项:
  --scan-root <目录>   数据盘根，写入代码 SCAN_ROOT 常量      (默认 /mnt/sda1/00.FTP)
  --tmp-dir  <目录>    zip 临时目录，写入代码 TMP_DIR 常量    (默认 /mnt/sda1/share-hub-tmp)
  --port     <端口>    服务端口                               (默认 8080)
  --share-dir <目录>   可选：部署完成后为首条链接指向的目录
  -y, --yes            免确认，未指定项全部取默认值
  --skip-sudo          跳过需要 sudo 的步骤（Tailscale 安装/登录/operator/linger），
                       适合已在别处完成或仅想验证脚本其余部分
  -h, --help           显示本帮助

前置条件: 本脚本须与 share-hub.py、share-hub.service 放在同一目录（即本仓库 Linux-Scripts/）。
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --scan-root) SCAN_ROOT="$2"; shift 2;;
        --tmp-dir)   TMP_DIR="$2"; shift 2;;
        --port)      PORT="$2"; shift 2;;
        --share-dir) SHARE_DIR="$2"; shift 2;;
        -y|--yes)    ASSUME_YES=1; shift;;
        --skip-sudo) SKIP_SUDO=1; shift;;
        -h|--help)   usage; exit 0;;
        *) echo "未知参数: $1"; usage; exit 1;;
    esac
done

log()  { echo "[setup-share-hub] $*"; }
die()  { echo "[setup-share-hub][错误] $*" >&2; exit 1; }
sudor() {
    if [[ $SKIP_SUDO -eq 1 ]]; then
        log "（--skip-sudo）跳过需要 sudo: $*"
    else
        sudo "$@"
    fi
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_PY="$SCRIPT_DIR/share-hub.py"
SRC_UNIT="$SCRIPT_DIR/share-hub.service"
[[ -f $SRC_PY && -f $SRC_UNIT ]] || die "缺少 $SRC_PY 或 $SRC_UNIT —— 请保持三件套在同一目录（仓库 Linux-Scripts/）"

# ---------- 1. Python 前置检查 ----------
command -v python3 >/dev/null || die "未找到 python3"
python3 - <<'EOF' || die "Python 版本过低（需 ≥ 3.7）"
import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)
EOF
log "Python: $(python3 --version)"

# ---------- 2. Tailscale 安装 ----------
if ! command -v tailscale >/dev/null; then
    if [[ $SKIP_SUDO -eq 1 ]]; then
        log "（--skip-sudo）未安装 Tailscale，跳过安装。请手动执行:"
        echo "    curl -fsSL https://tailscale.com/install.sh | sh"
    else
        log "未安装 Tailscale，尝试官方脚本安装（国内网络失败时请配代理后重试）…"
        curl -fsSL https://tailscale.com/install.sh | sh \
            || die "Tailscale 安装失败，请手动安装后重跑本脚本"
    fi
fi
command -v tailscale >/dev/null || die "tailscale 仍不可用"

# ---------- 3. Tailscale 登录 ----------
if ! tailscale status >/dev/null 2>&1; then
    log "Tailscale 未登录，发起登录（按提示用浏览器授权）…"
    sudor tailscale up
fi
tailscale status >/dev/null 2>&1 || die "Tailscale 未就绪，请检查网络/登录状态"
log "Tailscale: 已连接"

# ---------- 4. operator 免 sudo ----------
sudor tailscale set --operator="$USER"
log "operator 已设为 $USER（重复设置无害）"

# ---------- 5. 公网域名探测 ----------
PUBLIC_URL="$(tailscale status --json 2>/dev/null | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    n = ((d.get("Self") or {}).get("DNSName") or "").rstrip(".")
    print("https://" + n if n else "")
except Exception:
    print("")')"
if [[ -z $PUBLIC_URL ]]; then
    log "警告：未能自动取得 *.ts.net 域名（MagicDNS 未开？），links.json 的 public_base_url 留空，请登录后台补填"
fi
log "公网域名: ${PUBLIC_URL:-（未取得，稍后手动补）}"

# ---------- 6. 放置文件并适配路径 ----------
mkdir -p ~/.local/share/share-hub ~/.config/systemd/user ~/.config/share-hub
cp -f "$SRC_PY"   ~/.local/share/share-hub/share-hub.py
cp -f "$SRC_UNIT" ~/.config/systemd/user/share-hub.service
sed -i "s|^TMP_DIR = .*|TMP_DIR = \"$TMP_DIR\"|"             ~/.local/share/share-hub/share-hub.py
sed -i "s|^SCAN_ROOT = .*|SCAN_ROOT = \"$SCAN_ROOT\"|"       ~/.local/share/share-hub/share-hub.py
sed -i "s|^HOST, PORT = .*|HOST, PORT = \"127.0.0.1\", $PORT|" ~/.local/share/share-hub/share-hub.py
grep -q "^TMP_DIR = \"$TMP_DIR\""              ~/.local/share/share-hub/share-hub.py || die "TMP_DIR 写入失败"
grep -q "^SCAN_ROOT = \"$SCAN_ROOT\""          ~/.local/share/share-hub/share-hub.py || die "SCAN_ROOT 写入失败"
python3 -m py_compile ~/.local/share/share-hub/share-hub.py   || die "部署后的 share-hub.py 语法异常"
mkdir -p "$TMP_DIR"
log "文件已就位，常量已适配（SCAN_ROOT=$SCAN_ROOT TMP_DIR=$TMP_DIR PORT=$PORT）"

# ---------- 7. 配置文件 ----------
CFG=~/.config/share-hub/links.json
if [[ -f $CFG ]]; then
    log "配置已存在，跳过生成: $CFG"
else
    ADMIN_PW="$(python3 -c 'import secrets; print(secrets.token_urlsafe(9))')"
    SHARE_DIR="$SHARE_DIR" ADMIN_PW="$ADMIN_PW" PUBLIC_URL="$PUBLIC_URL" python3 - "$SHARE_DIR" <<'PYEOF'
import hashlib, json, os, secrets, sys
share_dir = sys.argv[1] if len(sys.argv) > 1 else ""
cfg = {
    "admin_password": os.environ["ADMIN_PW"],
    "public_base_url": os.environ["PUBLIC_URL"],
    "sessions": [],
    "links": {},
}
if share_dir and os.path.isdir(share_dir):
    tok = secrets.token_urlsafe(9)
    cfg["links"][tok] = {
        "name": os.path.basename(share_dir.rstrip("/")) or "分享",
        "path": os.path.realpath(share_dir),
        "note": "", "pw_hash": "", "created": __import__("time").strftime("%Y-%m-%d"),
    }
    print("SEED_LINK=" + tok)
p = os.path.expanduser("~/.config/share-hub/links.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
PYEOF
    log "已生成配置: $CFG"
    echo "=============================================="
    echo "  管理密码（只显示这一次，请妥善保存）: $ADMIN_PW"
    echo "=============================================="
    [[ -n $SHARE_DIR ]] && log "首条分享目录: $SHARE_DIR（链接见部署完成后输出）"
    [[ -z $SHARE_DIR ]] && log "未指定 --share-dir，请稍后在后台网页新建分享链接"
fi

# ---------- 8. Linger + 服务 ----------
sudor loginctl enable-linger "$USER"
systemctl --user daemon-reload
if systemctl --user is-active --quiet share-hub; then
    systemctl --user restart share-hub    # 让新常量生效
else
    systemctl --user enable --now share-hub
fi
for _ in $(seq 1 10); do
    sleep 0.5
    curl -s -o /dev/null "http://127.0.0.1:$PORT/healthz" && break
done
curl -s "http://127.0.0.1:$PORT/healthz" | grep -q ok || die "服务健康检查未通过，查看日志: journalctl --user -u share-hub -n 30"
log "share-hub 服务运行中 (127.0.0.1:$PORT)"

# ---------- 9. Funnel 公网映射 ----------
# 注意：不用「tailscale serve status | grep」管道判断——set -o pipefail 下
# grep -q 提前退出可能触发 SIGPIPE 竞态把整条管道判为失败；先捕获再匹配。
funnel_enabled() {
    local st
    st="$(tailscale serve status 2>&1 || true)"
    case "$st" in *"Funnel on"*) return 0;; *) return 1;; esac
}

if ! funnel_enabled; then
    FUNNEL_LOG="$(mktemp)"
    nohup tailscale funnel --bg "$PORT" > "$FUNNEL_LOG" 2>&1 &
    sleep 3
    AUTH_URL="$(grep -o 'https://login.tailscale.com/f/funnel[^[:space:]]*' "$FUNNEL_LOG" | head -1 || true)"
    if [[ -n $AUTH_URL ]]; then
        echo ""
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo "  Funnel 尚未开通，请用浏览器（任意设备，登录同一 Tailscale"
        echo "  账号）打开下面链接并点击开通，本脚本将自动等待生效："
        echo "  $AUTH_URL"
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    fi
    log "等待 Funnel 生效（最长 10 分钟，Ctrl+C 可中断，之后重跑本脚本即可续上）…"
    ok=0
    for _ in $(seq 1 120); do
        if funnel_enabled; then ok=1; break; fi
        sleep 5
    done
    rm -f "$FUNNEL_LOG"
    [[ $ok -eq 1 ]] || die "Funnel 未在等待期内生效；开通后重跑本脚本即可继续"
fi
log "Funnel 公网映射: 443 -> 127.0.0.1:$PORT"

# ---------- 10. 完成输出 ----------
echo ""
log "✅ 部署完成。入口信息："
echo "    管理后台 : ${PUBLIC_URL:-https://<你的域名>}/admin"
echo "    公网首页 : ${PUBLIC_URL:-https://<你的域名>}/ （中性页，无内容）"
[[ -f $CFG ]] && SEED_TOK="$(python3 -c '
import json
try:
    links = json.load(open("'"$CFG"'", encoding="utf-8"))["links"]
    print(next(iter(links), ""))
except Exception:
    print("")')"
[[ -n ${SEED_TOK:-} ]] && echo "    示例链接 : ${PUBLIC_URL:-https://<你的域名>}/s/$SEED_TOK"
echo ""
echo "后续：后台新建/管理分享链接；忘记管理密码看 $CFG；"
echo "详细运维见同目录 share-hub公网下载站部署与运维.md"
