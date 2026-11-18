#!/bin/bash
# 配置 vsftpd:将 /media/yym/3326F555A9DAFEB8/00.FTP 共享为 FTP 目录
# 用法: sudo bash /media/yym/3326F555A9DAFEB8/00.FTP/setup_ftp.sh
set -e

FTP_DIR="/media/yym/3326F555A9DAFEB8/00.FTP"
USER="yym"

echo "==> 1. 备份原配置"
cp -n /etc/vsftpd.conf /etc/vsftpd.conf.bak.$(date +%Y%m%d) || true
ls -l /etc/vsftpd.conf.bak.* 2>/dev/null || true

echo "==> 2. 写入新配置 /etc/vsftpd.conf"
cat > /etc/vsftpd.conf <<'EOF'
# ===== 基础设置 =====
listen=NO
listen_ipv6=YES
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022
dirmessage_enable=YES
use_localtime=YES
xferlog_enable=YES
connect_from_port_20=YES
secure_chroot_dir=/var/run/vsftpd/empty
pam_service_name=vsftpd
rsa_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem
rsa_private_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
ssl_enable=NO

# ===== 共享目录:登录后直接进入此目录,并限制在此目录内 =====
local_root=/media/yym/3326F555A9DAFEB8/00.FTP
chroot_local_user=YES
# NTFS 挂载目录权限为 777,vsftpd 默认拒绝 chroot 到可写目录,必须放开此限制
allow_writeable_chroot=YES

# ===== 只允许指定账号登录 FTP =====
userlist_enable=YES
userlist_file=/etc/vsftpd.userlist
userlist_deny=NO

# ===== 被动模式(客户端在局域网内必须)=====
pasv_enable=YES
pasv_min_port=40000
pasv_max_port=40100
EOF

echo "==> 3. 写入允许登录的账号列表 /etc/vsftpd.userlist"
echo "$USER" > /etc/vsftpd.userlist

echo "==> 4. 检查防火墙(若 ufw 启用则放行 FTP 端口)"
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
    ufw allow 20/tcp comment 'FTP data'
    ufw allow 21/tcp comment 'FTP control'
    ufw allow 40000:40100/tcp comment 'FTP passive'
    echo "    ufw 已放行 20/21 及 40000-40100 端口"
else
    echo "    ufw 未启用,无需额外放行"
fi

echo "==> 5. 重启 vsftpd"
systemctl restart vsftpd
systemctl --no-pager status vsftpd | head -5

echo ""
echo "✅ 配置完成!"
echo "   局域网访问地址:"
echo "     有线网段: ftp://192.168.1.137/"
echo "     无线网段: ftp://192.168.4.2/"
echo "   账号: $USER (密码为该 Linux 账号的登录密码)"
echo "   登录后直接进入 00.FTP 目录,可读写。"
