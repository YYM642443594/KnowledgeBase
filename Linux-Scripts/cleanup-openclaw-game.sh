#!/bin/bash
# 卸载为编译 OpenClaw 游戏而安装的所有依赖包
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get purge -y \
  libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libsdl2-gfx-dev \
  build-essential cmake
apt-get autoremove -y
echo "=== 卸载完成,确认无残留 ==="
dpkg -l | grep -E 'libsdl2[^ ]*-dev|build-essential|cmake ' || echo "已全部清除"
