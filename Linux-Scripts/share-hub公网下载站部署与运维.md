---
title: share-hub 公网下载站部署与运维
created: 2026-11-20
updated: 2026-11-21
tags: [Linux, 环境配置, Tailscale, 文件分享]
source: 原创
---

# share-hub 公网下载站部署与运维

> 本文档为 YYM 常用机专用运维记录，含本机绝对路径（换机器部署路径需自行调整）。

## 概述

本文记录 YYM 常用机（Ubuntu，机器名 `YYM`，Tailscale 主机名 `yym-2`）上「公网资料下载站」的架构、部署位置、日常操作与踩坑。核心结论：

- 给朋友发资料 = 发一条形如 `https://yym-2.tailb9678d.ts.net/s/<token>` 的链接，浏览器直接打开即可下载，**朋友侧无需安装任何软件（无需 Tailscale）**；
- 每个朋友一条独立链接、各绑一个目录，**相互隔离不可见**；单条链接可另设访问密码；
- **链接可设有效期与下载次数上限**（后台创建时填写），到期或达限自动失效；后台实时显示每条链接下载计数，可一键清零；
- 朋友侧页面右上角可切换**深/浅色**（默认浅色，偏好记忆在访问者浏览器里）；
- 管理入口 `/admin`（管理密码只存在本机配置文件里，因仓库公开不入库）。

## 正文

### 1. 功能演进（为什么是现在的形态）

| 时间 | 方案 | 问题 |
|------|------|------|
| 2026-11-20 上午 | dufs + Tailscale Funnel（单链接匿名只读） | 一条链接暴露整个目录，无隔离 |
| 2026-11-20 下午 | **share-hub + Funnel（现行）** | 按朋友隔离链接 + 管理后台 + 新 UI |

share-hub 为自制**单文件 Python 服务**（零第三方依赖，纯标准库），源码备份于本目录 [`share-hub.py`](share-hub.py)，systemd 单元为 [`share-hub.service`](share-hub.service)。本机运行副本在 `~/.local/share/share-hub/share-hub.py`（**以本机副本为准**，仓库内为备份；改动后需手动同步两处）。旧 dufs 二进制仍在 `~/.local/bin/dufs`，服务已 disable，仅留档。

### 2. 访问链路（朋友不需要 Tailscale）

```
朋友的浏览器（任意设备，无需 Tailscale、无需注册）
        │  https://yym-2.tailb9678d.ts.net/s/<token>
        ▼
Tailscale Funnel 边缘节点（公网入口，Tailscale 官方中转，自动签发 HTTPS 证书）
        │  Funnel 隧道
        ▼
本机 tailscaled (v1.104.6)，转发 443 → 127.0.0.1:8080
        ▼
share-hub（只监听 127.0.0.1:8080，局域网亦不可直接访问）
        ▼
本机磁盘上被分享的目录（只读）
```

关键区别：**普通 Tailscale** 组网要求对方装客户端进虚拟网；**Funnel** 是"公网发布"，全网任何人浏览器可访问。本方案只用 Funnel，朋友零要求。机器需开机在线（常开，远程开机用向日葵）。

### 3. 入口与凭证

| 入口 | 地址/位置 |
|------|-----------|
| 管理后台 | `https://yym-2.tailb9678d.ts.net/admin` —— 新建/删除分享链接、上传站点图标（页头+favicon，PNG/JPG/GIF/WEBP/SVG ≤2MB，可恢复默认芯片图标）、改公网地址与管理密码 |
| 管理密码 | 本机 `~/.config/share-hub/links.json` 的 `admin_password` 字段（**仓库公开，密码绝不入库**） |
| 链接清单 | 后台登录后可见全部；或看 `links.json` 的 `links` 键 |
| 本机健康检查 | `curl http://127.0.0.1:8080/healthz` 返回 `ok` |
| 公开分享区示例链接 | `https://yym-2.tailb9678d.ts.net/s/aC03SVGnzn_B` → `/mnt/sda1/00.FTP/99.公开分享` |

### 4. 部署清单（都在哪）

| 内容 | 位置 |
|------|------|
| 服务程序 | 本机 `~/.local/share/share-hub/share-hub.py`；备份 `Linux-Scripts/share-hub.py` |
| systemd 用户服务 | `~/.config/systemd/user/share-hub.service`（开机自启，Linger=yes 已开） |
| 配置文件 | `~/.config/share-hub/links.json`（链接表/管理密码/公网地址） |
| Funnel 映射 | tailscaled 内置持久化（443 → 8080，重启自动恢复） |
| zip 打包临时目录 | `/mnt/sda1/share-hub-tmp`（超过 2 小时自动清理） |
| tailscale operator | 已设为 yym（`sudo tailscale set --operator=yym` 一次性），CLI 免 sudo |

配置文件格式（`links.json`）：

```json
{
  "admin_password": "只在本机",
  "public_base_url": "https://yym-2.tailb9678d.ts.net",
  "sessions": [],
  "links": {
    "<token>": {
      "name": "朋友看到的名字", "path": "/绝对路径/目录或文件",
      "note": "显示给朋友的备注", "pw_hash": "SHA-256(访问密码)或空",
      "created": "YYYY-MM-DD"
    }
  }
}
```

### 5. 日常操作

给新朋友分享：资料放任意目录 → 后台 ➕ 新建分享（名称/选目录/可选密码/有效期/下载次数上限）→ 复制生成的 `/s/xxxx` 链接发出去。资料放进目录即时生效，无需重启。

命令速查：

```bash
systemctl --user status|restart|stop share-hub   # 服务管理
journalctl --user -u share-hub -f                # 实时访问日志
tailscale serve status                           # 查 Funnel 映射（应显示 443→8080）
tailscale funnel --bg 8080                       # 重建映射（配置丢失时）
tailscale funnel --https=443 off                 # 彻底关闭公网入口
systemctl --user disable --now share-hub         # 彻底下线服务
```

### 6. 安全模型

- **隔离**：每条链接只绑定一个目录，页面只渲染该目录内容，链接间零引用；
- **token 即凭证**：随机 12 字符（72 bit），无效 token 一律返回中性 404；
- **只读**：服务只有 GET/HEAD 路由，无上传/删除接口；
- **路径防护**：realpath 归一化，越出分享根目录（及 `/mnt/sda1/00.FTP` 软链白名单区）即 404，`..` 与反斜杠直接拒绝；
- **密码保护**（可选）：SHA-256 存哈希，Cookie HttpOnly + SameSite=Lax；
- **最小暴露**：8080 只绑 127.0.0.1；公网仅 Funnel 443 一个入口；页面带 `noindex`。

### 7. 已验证测试（2026-11-20）

后台登录（401/303）、建链删链即时失效、链接隔离、中文文件名下载、Range 断点续传（206）、文件夹打包 zip（完整性校验）、无效 token 404、目录穿越 404、Funnel 公网访问——全部通过。

2026-11-21 增补：深/浅色切换（按钮/深色变量/localStorage 记忆）、有效期（昨日过期链接 410、明日有效链接 200）、限次（上限 2 次第 3 次 410、后台显示 2/2、清零恢复下载）——全部通过。

### 8. 踩坑记录

1. **Funnel 开通需账号级授权**：`tailscale funnel` 首次使用会给出一条 `login.tailscale.com/f/funnel?node=…` 链接，须由账号本人在浏览器里点开通；本机 CLI 还需先 `sudo tailscale set --operator=$USER` 才能写 serve 配置。
2. **后台「公网地址」字段改错导致链接打不开**（2026-11-20 实踩）：该字段**只是后台显示用前缀**，不产生任何路由；真实公网入口只能由 Funnel 决定（`*.ts.net`）。误改成自有域名后，复制的链接全部指向无 DNS/隧道的域名。修复：改回 `https://yym-2.tailb9678d.ts.net` 即可，即时生效。想真正用自己的域名须换 Cloudflare Tunnel 等方案。
3. **systemd 单元路径里的 `%` 是转义前缀**：ExecStart 里用百分号 URL 编码中文路径会被 systemd 当 specifier 解析报"bad unit file setting"，直接写 UTF-8 中文即可。
4. **本机网络对 GitHub 大传输不友好**：git 推送偶发 TLS 中断，重试或换 SSH 远程（`git@github.com:`）通常可过；详见 [Linux 常用机脚本 Readme](Readme.md) 同机的网络方案。

### 9. FAQ

**Q：朋友电脑没装 Tailscale 能访问吗？**
能，完全不需要。Funnel 是公网发布，任意浏览器直接打开；Tailscale 只需装在本机（负责隧道）。

**Q：下载速度如何？**
取决于家庭宽带上行带宽，且经 Tailscale 边缘中转有少量开销；多人同时下载互相占带宽。

**Q：朋友打不开链接怎么排查？**
① 本机 `curl http://127.0.0.1:8080/healthz` 应返回 `ok`；② `tailscale serve status` 应显示 Funnel on；③ 机器是否开机在线；④ 让朋友换网络重试（个别运营商访问 `*.ts.net` 偶发不畅）。

**Q：重启电脑后还在吗？**
在。systemd 用户服务 + Linger=yes 开机自启；Funnel 映射由 tailscaled 持久化。

**Q：最多能建多少条分享链接？**
代码无上限：链接就是 links.json 里的字典条目，token 空间 72 bit（约 4.7×10²¹ 组合，碰撞概率可忽略）。
2026-11-20 实测：1 万条链接时单请求总耗时 53~85ms（配置解析约 31ms），完全可用；
日常几十条毫无压力。唯一会随数量变慢的是管理后台（全量渲染表格），数千条以上如需顺畅可加分页/搜索。

**Q：链接过期或达到下载上限后，朋友看到什么？**
后台对应行标红并注明"已失效（过期/超限）"；朋友访问返回"链接已失效"
提示页（HTTP 410）。过期需删除重建链接重新分发；仅计数达限时点"清零"
按钮即可恢复下载。

**Q：页面可以切换深浅色吗？**
可以，浏览页右上角月亮/太阳按钮，偏好保存在访问者浏览器
（localStorage），默认浅色。

**Q：以后想加链接有效期/下载次数/独立域名？**
有效期与计数：改 `share-hub.py`（`links.json` 加字段 + 下载计数逻辑）；独立域名：换 Cloudflare Tunnel 替代 Funnel，服务层不用动。

### 10. 换机从零部署清单（新机器重建）

> **一键脚本**：`Linux-Scripts/setup-share-hub.sh` 可自动完成本节第 1~8 步（幂等，支持
> `--yes` 免交互与 `--skip-sudo`；用法见 [Readme.md](Readme.md) 第 7 节）。以下为手动等价
> 步骤与原理说明。

> 前提：Ubuntu/Debian 系 Linux，Python ≥ 3.7（本机实测 3.10），机器常开在线；
> Tailscale 客户端任意近期版本均可（本机实测 1.104.6）。

> 前提：Ubuntu/Debian 系 Linux，Python ≥ 3.7（本机实测 3.10），机器常开在线；
> Tailscale 客户端任意近期版本均可（本机实测 1.104.6）。

1. **装并登录 Tailscale**（同一账号）：
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```
2. **授权 CLI**（免 sudo）：`sudo tailscale set --operator=$USER`
3. **开通 Funnel**：随便执行一次 `tailscale funnel --bg 8080`，它会打印一条
   `https://login.tailscale.com/f/funnel?node=…` 授权链接，由账号本人在浏览器点击开通
   （管理台需开启 MagicDNS 与 HTTPS Certificates，链接页会引导）。
4. **放置文件**（源：本仓库 `Linux-Scripts/`）：
   ```bash
   mkdir -p ~/.local/share/share-hub
   cp Linux-Scripts/share-hub.py ~/.local/share/share-hub/
   cp Linux-Scripts/share-hub.service ~/.config/systemd/user/   # 目录不存在先建
   ```
5. **改适配本机的常量**（都集中在 `share-hub.py` 文件头部）：
   - `TMP_DIR`（zip 临时目录，指向空间足够的盘）
   - `SCAN_ROOT`（后台目录下拉的扫描根，如新机器的数据盘根）
   - `HOST/PORT`（一般不用改：127.0.0.1:8080）
   - `share-hub.service` 的 `ExecStart` 里分享根目录路径同步改；
6. **开 Linger**（否则重启后用户服务不启动，下载站失联）：
   `sudo loginctl enable-linger $USER`
7. **建配置**：
   ```bash
   mkdir -p ~/.config/share-hub
   # 按第 4 节格式手写 links.json；admin_password 用
   # python3 -c "import secrets;print(secrets.token_urlsafe(9))" 生成
   # public_base_url 填新机器的 https://<新主机名>.<tailnet域名>.ts.net
   ```
8. **启动**：
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now share-hub
   tailscale funnel --bg 8080
   ```
9. **验证**：`curl http://127.0.0.1:8080/healthz` 返回 `ok` →
   `tailscale serve status` 显示 443→8080 → 浏览器打开公网链接能列出文件 →
   走一遍第 7 节的关键测试（下载/打包/隔离/穿越 404）。

⚠️ **换机迁移注意**：新机器的 `*.ts.net` 主机名必然不同，**旧机器发出去的所有朋友链接全部失效**——需在新机器后台按 `links.json` 重建同名目录与链接后重新分发给朋友；确认新机正常后再对旧机器执行 `tailscale funnel --https=443 off` 与 `systemctl --user disable --now share-hub` 下线。

## 总结

方案最终形态：share-hub（单文件只读下载站，按朋友隔离链接）+ Tailscale Funnel（公网入口）+ systemd 用户服务（开机自启）。运维只需记三件事：后台建链发链接、`systemctl --user` 管服务、`tailscale serve status` 查公网映射。后续如需自定义域名，迁移路径为 Cloudflare Tunnel。

## 参考

- 本仓库：[share-hub.py](share-hub.py)（源码备份）、[share-hub.service](share-hub.service)（服务单元备份）、[Linux 常用机脚本 Readme](Readme.md)
- [Tailscale Funnel 官方文档](https://tailscale.com/kb/1223/funnel)
- [Tailscale Serve 官方文档](https://tailscale.com/kb/1312/serve)
