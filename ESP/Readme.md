# ESP 知识库

> 2026-10-26 重组：原三个顶层目录 ESP-32、ESP-32-CAM、ESP-8266 收纳至本知识库，**按芯片平台划分目录**（一个平台目录 = 一个固件工程），与 IMU 知识库同一组织方式。各平台固件版本、硬件占用、验证手册、踩坑记录见对应目录 Readme。

## 平台目录与工程映射

| 目录（芯片平台） | 固件工程 | 主控 | SDK/框架 | 代码仓 / 分支 |
|------------------|----------|------|----------|---------------|
| [ESP-32/](ESP-32/) | 串口 ↔ WiFi/蓝牙透传 + 网页终端（配网/串口终端/转发三标签） | ESP32-WROOM-32（ESP32-D0WDQ6，双核 LX6 @ 240MHz，4MB Flash） | ESP-IDF v6.1 | gitee `ESP.git` develop 分支 |
| [ESP-32-CAM/](ESP-32-CAM/) | 网页视频监控（OV3660 + SD 录像 + 人体检测 + 邮件推送 + 场景联动） | AI-Thinker ESP32-CAM（实测 OV3660，4MB Flash / 8MB PSRAM） | ESP-IDF v6.1 + esp32-camera 2.1.8 | gitee `ESP.git` feature/ESP32-Camer 分支（Linux 本地副本 `/home/yym/sda1/ESP`） |
| [ESP-8266/](ESP-8266/) | ESP8266-XCOM 串口 WiFi 透传器（五云平台桥 + GPIO 控制 + 防克隆绑定） | ESP8266（NodeMCU v2，板载 CH340） | PlatformIO + Arduino | ESP8266 仓库（远程经 SSH 别名 `git@github-esp8266`） |

> 两个 ESP32 工程同一代码仓不同分支：develop = 串口透传，feature/ESP32-Camer = 摄像头监控。新工程 = 新芯片平台时登记本表并新建同名目录；同平台新功能更新对应目录 Readme，不新建目录。

## 目录结构

```text
ESP/
├── Readme.md      ← 本索引（工程映射、文档索引、跨平台知识链、归档规则）
├── ESP-32/        ← 串口透传工程（ESP-IDF，APP→BSP→DRV→HAL→ESP-IDF 四层）
│   ├── Readme.md
│   ├── Project_Level_Skill.md   ← ESP-IDF 版架构规范
│   ├── 一键烧录.bat
│   └── Doc/                     ← 参考实现（drv_key 按键状态机源码）
├── ESP-32-CAM/    ← 视频监控工程（ESP-IDF）
│   └── Readme.md
└── ESP-8266/      ← XCOM 透传工程（Arduino，main→APP→BSP→HAL→Arduino）
    ├── Readme.md
    ├── Project_Level_Skill.md   ← Arduino 版架构规范
    └── Cloud_Protocol.md        ← 五云平台协议细节
```

> ESP-32 与 ESP-8266 的 Project_Level_Skill.md 因框架不同（ESP-IDF vs Arduino）内容不同，各自保留在平台目录内。

## 文档索引

| 平台目录 | 文档 | 主题 |
|----------|------|------|
| ESP-32 | [Readme.md](ESP-32/Readme.md) | 全模块 HAL/BSP/APP 功能记录、硬件资源表、8 条数据通路、回显/按键/配网/蓝牙/NAT/转发验证手册、MCU 移植提示 |
| ESP-32 | [Project_Level_Skill.md](ESP-32/Project_Level_Skill.md) | ESP-IDF 四层架构规范（命名/裁剪开关/分层依赖/移植规则） |
| ESP-32-CAM | [Readme.md](ESP-32-CAM/Readme.md) | 摄像头监控全记录（hal_cam/SD 录像/检测/邮件/场景联动）+ 31 条踩坑 + 遗留 Bug 表 + 版本历史 |
| ESP-8266 | [Readme.md](ESP-8266/Readme.md) | XCOM 全记录（透传/转发/五云桥/GPIO 闹钟/防克隆）+ 7 条数据通路 + 踩坑表 + 版本修改史 |
| ESP-8266 | [Project_Level_Skill.md](ESP-8266/Project_Level_Skill.md) | Arduino 单仓分层规范（形态B：HAL 在 01.HAL/，BSP/APP 在 modules/） |
| ESP-8266 | [Cloud_Protocol.md](ESP-8266/Cloud_Protocol.md) | 阿里/OneNET/巴法/腾讯/华为五云平台指令表、签名格式、主题语义 |

## 跨平台知识链（三工程共通谱系）

```text
[ESP-8266] ESP8266-develop 工程（配网门户+WS 终端+转发雏形）
      │  网页谱系移植
      ├────────────▶ [ESP-32] bsp_web 三标签门户（配网/串口终端/转发）
      │                      │ 同栈移植 + 摄像头扩展
      │                      ▼
      │              [ESP-32-CAM] 四标签门户（配网/视频监控/GPIO 控制/存储）
      └────────────▶ [ESP-8266] XCOM 五标签门户（+物联网平台/GPIO 控制）
```

| 共通主题 | 结论 | 出处 |
|----------|------|------|
| 配网模型 | SoftAP `ESP32_Config`/192.168.4.1 常开 + NVS 持久化凭据 + 断线自动重连 | ESP-32 / ESP-32-CAM hal_wifi；ESP-8266 AP 常开 |
| 断线重连策略 | 按原因分类：瞬时类（NO_AP_FOUND/信标丢失）无限退避重连；认证类（密码错）限次防死循环 | ESP-32-CAM 踩坑 19（V1.3.0.3）；ESP-8266 退避 4s→16s→64s→256s 封顶 300s |
| NAPT 借道上网 | STA 联网即开 NAPT（`LWIP_IP_FORWARD`+`LWIP_IPV4_NAPT`），断开自动关；单射频预期 10~20Mbps | ESP-32 / ESP-32-CAM hal_wifi |
| WS 网页终端 | :81 端口二进制通道广播串口数据；慢客户端处理：ESP-32 登记表+合批缓冲（30ms 合帧），ESP-8266 心跳剔除僵尸+逐客户端发送 | ESP-32 bsp_web；ESP-8266 V1.0.5.19 补丁 |
| 阻塞 connect 卡主循环 | 建链前置校验（凭据/NTP 门控）+ 非阻塞退避，DNS/TCP 同步阻塞会冻结轮询数秒 | ESP-8266 V1.0.2.7 / V1.0.5.1；ESP-32 转发用非阻塞 connect+select |
| Mesh/多 AP 同名 | STA 钉住 BSSID+信道免扫描重连（扫描期间 SoftAP 停发信标），8 次失败解锁重扫 | ESP-32-CAM 踩坑 26（V1.3.0.6） |
| 烧录口纪律 | Linux YYM 机：ESP32-CAM=/dev/ttyUSB1、ESP8266=/dev/ttyUSB0，均 115200（460800 失联）；烧录前后检查 serial_sim.py 存活；ESP32-CAM 构建/烧录须 `export IDF_TOOLS_PATH=/home/yym/sda1/espressif`（配置在 /mnt/sda1 会被拒：python_env 实际在 /home/yym/sda1，双目录易混） | ESP-32-CAM 硬件表/踩坑 22/版本历史 V1.4.2.10 复测行 |

## 归档规则

1. 文档按**所属固件工程（芯片平台）**归档入对应目录；同平台新报告入该目录，并在本索引「文档索引」表登记
2. 跨平台通用经验不单独建目录，沉淀到本索引「跨平台知识链」区并链接原始文档
3. 文档内引用其它平台文档一律用相对链接（如 `../ESP-32/Readme.md`），不写旧顶层目录路径
