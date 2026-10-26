#!/bin/bash
# 安装并配置 vsftpd,共享目录为 /mnt/sda1/00.FTP
set -e

# 1. 安装 vsftpd
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y vsftpd

# 2. 备份原配置并写入新配置
cp /etc/vsftpd.conf /etc/vsftpd.conf.bak-$(date +%Y%m%d-%H%M%S)
cat > /etc/vsftpd.conf <<'EOF'
# ===== vsftpd 配置(共享目录 /mnt/sda1/00.FTP)=====
# 监听 IPv4,独立模式
listen=YES
listen_ipv6=NO

# 使用系统账号登录(用户:yym,密码:系统登录密码),禁止匿名
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022
connect_from_port_20=YES

# 所有登录用户都锁定在共享目录内(无法访问系统其他目录)
chroot_local_user=YES
allow_writeable_chroot=YES
local_root=/mnt/sda1/00.FTP

# 被动模式端口范围
pasv_enable=YES
pasv_min_port=40000
pasv_max_port=40100

# 传输日志
xferlog_enable=YES
log_ftp_protocol=YES
EOF

# 3. 确保共享目录存在,启动并设置开机自启
[ -d /mnt/sda1/00.FTP ] || mkdir -p /mnt/sda1/00.FTP
systemctl enable --now vsftpd
systemctl restart vsftpd

echo "=== 服务状态 ==="
systemctl is-active vsftpd
ss -tlnp | grep -E ':21\b'
