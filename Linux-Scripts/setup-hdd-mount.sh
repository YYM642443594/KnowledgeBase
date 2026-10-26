#!/bin/bash
# 将机械硬盘 sda 的两个分区设置为开机自动挂载到 /mnt,挂载点与分区名一致
set -e

# 1. 创建挂载点(与分区名 sda1 / sda2 保持一致)
mkdir -p /mnt/sda1 /mnt/sda2

# 2. 备份 fstab
cp /etc/fstab /etc/fstab.bak-$(date +%Y%m%d-%H%M%S)

# 3. 写入挂载配置(按 UUID 挂载,不依赖设备名;nofail 防止硬盘故障时卡开机)
grep -q '0f750702-6c97-495e-83ba-f5538b7796bf' /etc/fstab || cat >> /etc/fstab <<'EOF'

# 机械硬盘 (sda) 分区自动挂载,挂载点与分区名一致
UUID=0f750702-6c97-495e-83ba-f5538b7796bf  /mnt/sda1  ext4  defaults,nofail  0  2
UUID=3790e7e8-1daa-4a80-b352-61d74f82a30b  /mnt/sda2  ext4  defaults,nofail  0  2
EOF

# 4. 立即挂载并把目录所有权给 yym
mount -a
chown yym:yym /mnt/sda1 /mnt/sda2

echo "=== fstab 新增内容 ==="
tail -4 /etc/fstab
echo "=== 挂载结果 ==="
df -h /mnt/sda1 /mnt/sda2
