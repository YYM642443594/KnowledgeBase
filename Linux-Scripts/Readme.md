# Linux 常用机脚本

> 2026-10-26 建：备份自 `/home/yym/sda1/00.FTP` 的常用环境配置脚本。全部通过 `bash -n` 语法检查；带 `sudo` 需求的脚本请用 root 运行。

## 脚本总览

| 脚本 | 用途 | 权限 | 交互 |
|------|------|------|------|
| [claude-setup.sh](claude-setup.sh) | Claude Code 一键安装配置（多平台） | 普通用户（链接环节可免 sudo） | 菜单 / 免交互均可 |
| [openclaw-setup.sh](openclaw-setup.sh) | OpenClaw AI 助理网关一键安装配置 | 普通用户（链接环节可免 sudo） | 主菜单 / 免交互均可 |
| [setup-ftp.sh](setup-ftp.sh) | vsftpd FTP 服务一键配置（共享 /mnt/sda1/00.FTP） | root | 无 |
| [setup_ftp.sh](setup_ftp.sh) | vsftpd FTP 服务配置（U 盘目录旧版，含防火墙放行） | root | 无 |
| [setup-hdd-mount.sh](setup-hdd-mount.sh) | 机械硬盘两分区 fstab 开机自动挂载 | root | 无 |
| [cleanup-openclaw-game.sh](cleanup-openclaw-game.sh) | 卸载 OpenClaw 游戏编译所装的全部依赖 | root | 无 |

---

## 1. claude-setup.sh — Claude Code 一键安装配置

安装 Node.js（国内镜像、用户目录）+ Claude Code CLI，并把 Claude Code 接入所选模型平台（智谱 GLM / Kimi / DeepSeek / Anthropic 官方 / 第三方中转站 / 自定义），配置写入 `~/.claude/settings.json`（权限 600，旧配置自动备份）。

### 用法

```bash
bash claude-setup.sh            # 全流程：安装环境 → 选平台 → 配置 → 验证
bash claude-setup.sh install    # 仅安装环境（Node.js + Claude Code + 全局命令）
bash claude-setup.sh config     # 仅配置接入平台（菜单选择 + 输入 Key）
bash claude-setup.sh show       # 查看当前配置（Token 自动打码）
bash claude-setup.sh doctor     # 诊断：版本 + API 连通性实测
bash claude-setup.sh help       # 显示帮助
```

### 参数

| 参数 | 作用 |
|------|------|
| `install` / `config` / `show` / `doctor` / `help` | 子命令，分别对应只装环境 / 只配平台 / 查配置 / 诊断 / 帮助；无子命令 = 全流程 |
| `--base-url <URL>` | 指定 API 地址，跳过平台选择菜单（结尾 `/` 自动去除） |
| `--token <KEY>` | 指定 API Key，跳过输入（输入时不回显） |
| `--model <名称>` | 指定默认主模型（如 `glm-4.6`），写入 `ANTHROPIC_MODEL` |
| `--timeout <秒>` | API 超时秒数，写入 `API_TIMEOUT_MS`；不指定时交互菜单选（默认 600 秒） |
| `--perm <模式>` | 文件修改权限模式：`default`（每次询问）/ `acceptEdits`（自动接受编辑）/ `plan`（只规划）/ `bypassPermissions`（全自动，有风险）；`default` 等于不写该字段 |
| `-y`, `--yes` | 免确认：未指定的项全部取默认值（超时 600s、权限模式不设置、主题跳过） |

### 说明

- 平台预设含官方地址与推荐模型（如 GLM：`glm-5.3-flash|glm-4.6|...`），选平台后自动带出；后台小模型（`ANTHROPIC_SMALL_FAST_MODEL`）按平台自动设置
- Node.js v20.18.1 装到 `~/.local/share/nodejs`（npmmirror 镜像，支持 x64/arm64）；系统已有 Node ≥ 18 则跳过
- 命令链接：有 sudo 时软链到 `/usr/local/bin`；无 sudo 自动改为写 `~/.bashrc` / `~/.profile` PATH
- 免交互示例：`claude-setup.sh config --base-url https://xxx --token sk-xxx --yes`

---

## 2. openclaw-setup.sh — OpenClaw 一键安装配置

OpenClaw（原 Clawdbot/Moltbot，开源个人 AI 助理网关，可接 WhatsApp/Telegram/Discord 等渠道）的环境安装与模型接入配置，写入 `~/.openclaw/openclaw.json`（权限 600，旧配置自动备份）。

### 用法

```bash
bash openclaw-setup.sh           # 无参数 → 主菜单（安装/配置/查询/诊断）
bash openclaw-setup.sh full      # 全流程：安装环境 → 选平台 → 配置 → 验证
bash openclaw-setup.sh install   # 仅安装环境（Node 26 + OpenClaw + 全局命令）
bash openclaw-setup.sh config    # 仅配置模型接入
bash openclaw-setup.sh show      # 查看当前配置（Key 自动打码）
bash openclaw-setup.sh doctor    # 诊断：Node/OpenClaw 版本 + API 连通性
bash openclaw-setup.sh help      # 显示帮助
```

### 参数

| 参数 | 作用 |
|------|------|
| `full` / `install` / `config` / `show` / `doctor` / `help` | 子命令；无参数弹主菜单，有选项但无子命令时按 `full` 处理 |
| `--base-url <URL>` | 指定 API 地址，跳过平台菜单（提供商记为 `custom`） |
| `--token <KEY>` | 指定 API Key，跳过输入 |
| `--model <名称>` | 指定默认模型；`--yes` 且未指定时用 `claude-sonnet-4-5` |
| `-y`, `--yes` | 免确认（已有配置直接覆盖；未指定模型给默认值） |

### 说明

- **Node 版本要求**：OpenClaw 要求 Node ≥ 26.12.1，脚本安装 Node v26.12.1；**重装前先删旧目录再解压**（避免 npm 新旧混装损坏；全局包如 claude-code 会被清掉并在后续自动恢复）
- OpenClaw 经 npmmirror 镜像 npm 全局安装；第二步带 `--allow-scripts` 允许内置插件安装脚本（npm 11 默认拦截）
- 平台模型全部写入配置（含上下文窗口/最大输出元数据），便于后续切换；完成后提示 `openclaw onboard`（接渠道）/ `openclaw gateway`（启动网关）
- 覆盖已有配置前会警告确认（渠道等设置建议先 `openclaw onboard` 再改模型）

---

## 3. setup-ftp.sh — vsftpd FTP 服务一键配置（当前使用版）

安装并配置 vsftpd，把 `/mnt/sda1/00.FTP` 共享为 FTP 根目录：系统账号登录（yym + 系统密码）、禁止匿名、用户锁定在共享目录内、被动模式端口 40000-40100、开启传输日志。

### 用法

```bash
sudo bash setup-ftp.sh
```

无参数。流程：装 vsftpd → 备份并重写 `/etc/vsftpd.conf` → 建共享目录 → `systemctl enable --now` → 打印服务状态与 21 端口监听。

### 配置要点（脚本内写死，如需变更改脚本）

| 配置项 | 值 |
|--------|-----|
| `local_root` | `/mnt/sda1/00.FTP`（登录后直接进入并锁定） |
| `anonymous_enable` | NO（禁止匿名） |
| 被动端口 | 40000~40100 |
| 配置备份 | `/etc/vsftpd.conf.bak-时间戳` |

---

## 4. setup_ftp.sh — vsftpd FTP 服务配置（U 盘目录旧版）

旧版配置：共享目录为 U 盘 `/media/yym/3326F555A9DAFEB8/00.FTP`（NTFS，777 权限）。与上一版差异：IPv6 监听、`userlist` 白名单只允许 yym 登录、**ufw 启用时自动放行 20/21/40000-40100 端口**。

### 用法

```bash
sudo bash setup_ftp.sh
```

无参数（脚本头部注释含历史用法示例）。要求 vsftpd 已安装（只改配置不装包）。

### 配置要点

| 配置项 | 值 |
|--------|-----|
| `local_root` | `/media/yym/3326F555A9DAFEB8/00.FTP` |
| `userlist` | `/etc/vsftpd.userlist` 仅 yym |
| `allow_writeable_chroot` | YES（NTFS 777 目录必需，否则 vsftpd 拒绝 chroot） |
| 局域网地址 | 有线 `ftp://192.168.1.137/`、无线 `ftp://192.168.4.2/`（脚本输出提示） |

> 两份 FTP 脚本二选一，按共享目录位置选择；重复运行均幂等（先备份原配置）。

---

## 5. setup-hdd-mount.sh — 机械硬盘开机自动挂载

把机械硬盘 sda 的两个 ext4 分区按 **UUID** 写入 `/etc/fstab` 开机自动挂载到 `/mnt/sda1`、`/mnt/sda2`（挂载点与分区名一致），`nofail` 防止硬盘故障卡开机。

### 用法

```bash
sudo bash setup-hdd-mount.sh
```

无参数。流程：建挂载点 → 备份 fstab → fstab 无对应 UUID 时追加两行配置 → `mount -a` 立即挂载 → 目录所有权给 yym → 打印 fstab 新增内容与挂载结果。

### 注意

- **脚本内 UUID 为本机（YYM 机）硬盘专用**，换机器必须先用 `blkid` 查新 UUID 并改脚本第 15~16 行
- `defaults,nofail`：硬盘缺席/故障时跳过挂载正常开机；第 5 字段 `2` 表示非根分区 fsck
- 幂等：grep 检测 UUID 已存在则不重复追加

---

## 6. cleanup-openclaw-game.sh — 卸载 OpenClaw 游戏编译依赖

清理为编译 OpenClaw 游戏（SDL 复刻版）而安装的全部依赖：`libsdl2-*` 全家桶 + `build-essential` + `cmake`，`apt-get purge` 后 `autoremove`，最后检查无残留。

### 用法

```bash
sudo bash cleanup-openclaw-game.sh
```

无参数。**注意**：会连带卸载 `build-essential` 与 `cmake`，若系统其他开发工作依赖它们请先确认。
