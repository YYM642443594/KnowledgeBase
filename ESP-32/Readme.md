# ESP32-WROOM-32 工程功能记录

- **MCU**：ESP32-WROOM-32（SoC：ESP32-D0WDQ6，双核 Xtensa LX6 @ 240MHz，4MB Flash / 520KB SRAM）
- **SDK**：ESP-IDF **v6.1**（本机安装于 `F:\00.Code\11ESP\esp-idf`，工具链 `D:\software\31ESP`，激活脚本 `F:\00.Code\11ESP\idf-env.bat`；v5.x 亦可编译）
- **架构**：`APP → BSP → DRV → HAL → ESP-IDF` 四层单向依赖，规范见 [Project_Level_Skill.md](Project_Level_Skill.md)
- **IDE**：VS Code（Trae）+ ESP-IDF 扩展，或 idf.py 命令行

## 目录结构

```text
ESP-32/
├── inc/                       ← 四层头文件平铺（文件名前缀区分层级）
│   ├── cfg_modules.h          ← 功能裁剪开关宏（CFG_XXX_EN）
│   ├── hal_uart.h
│   ├── hal_led.h
│   ├── hal_key.h
│   ├── hal_http.h
│   ├── hal_spp.h
│   ├── hal_wifi.h
│   ├── bsp_uart.h
│   ├── bsp_led.h
│   ├── bsp_key.h
│   ├── bsp_bt.h
│   ├── bsp_web.h
│   ├── bsp_wifi.h
│   ├── app_uart.h
│   ├── app_led.h
│   ├── app_key.h
│   ├── app_net.h
│   └── app_main.h
├── src/                       ← 与 inc/ 同名对应
│   ├── hal_uart.c
│   ├── hal_led.c
│   ├── hal_key.c
│   ├── hal_http.c
│   ├── hal_spp.c
│   ├── hal_wifi.c
│   ├── bsp_uart.c
│   ├── bsp_led.c
│   ├── bsp_key.c
│   ├── bsp_bt.c
│   ├── bsp_web.c
│   ├── bsp_wifi.c
│   ├── app_uart.c
│   ├── app_led.c
│   ├── app_key.c
│   ├── app_net.c
│   └── app_main.c
├── CMakeLists.txt             ← 工程构建入口
├── main/CMakeLists.txt        ← 汇总 src/*.c 到 main 组件
├── partitions.csv             ← 自定义分区表（4MB Flash：nvs 24KB + factory 3MB）
├── sdkconfig.defaults         ← 首次构建默认配置（生成 sdkconfig 后纳入版本管理）
└── Readme.md
```

## 硬件资源占用表

| 外设 | 引脚/资源 | 用途 | 归属模块 |
|------|-----------|------|----------|
| UART0 | TX=GPIO1 / RX=GPIO3，115200-8N1 | 调试口（与日志输出/固件下载复用；`BSP_UART_DBG_EN` 控制是否挂驱动，挂驱动后控制台接收被接管） | hal_uart / bsp_uart |
| UART1 | TX=GPIO18 / RX=GPIO19，115200-8N1 | 扩展口（GPIO 矩阵重映射，模组默认脚 9/10 接 Flash 不可用；`BSP_UART_EXT_EN` 控制） | hal_uart / bsp_uart |
| UART2 | TX=GPIO17 / RX=GPIO16，115200-8N1 | 通信口（**网页串口工具/蓝牙 SPP 透传口**，波特率可经网页在线修改；`BSP_UART_COMM_EN` 控制） | hal_uart / bsp_uart / app_net |
| GPIO2 | GPIO2，推挽输出 | 板载运行指示灯（DevKitC 板载 LED） | hal_led / bsp_led / app_led |
| GPIO0 | GPIO0，输入上拉，低有效 | 板载 BOOT 按键（DevKitC 板载，默认绑定；**Strapping 脚**：上电时按住进下载模式，运行期作普通按键无影响） | hal_key / bsp_key / app_key |
| WiFi | 射频（无引脚）；SoftAP `ESP32_Config`/192.168.4.1 + STA | 配网热点常开 + 凭据连接路由（NVS 持久化，断线自动重连）；**STA 联网后热点开 NAPT 中继，手机连热点即可借道上网**；与蓝牙共存（`ESP_COEX_SW_COEXIST_ENABLE`） | hal_wifi / bsp_wifi / app_net |
| BT | 射频（无引脚）；经典蓝牙 SPP 服务端 `ESP32-UART` | 蓝牙串口透传通道（手机/电脑蓝牙串口客户端接入） | hal_spp / bsp_bt / app_net |

> ESP32-WROOM-32 共 3 路硬件串口，全部已在 `bsp_uart.h` 建档（使能开关 + 波特率 + 引脚集中配置），按需启用；GPIO16/17 在 WROOM-32 上空闲，若换 WROVER 模组此两脚被 PSRAM 占用，须改引脚（改 `bsp_uart.h` 宏即可）。按键槽位与 GPIO 解耦：`app_key.h` 宏改一个 GPIO 号即可把任意空闲脚绑为按键（GPIO6~11 连接模组 Flash 被黑名单拒绝；GPIO34~39 仅输入且无内部上下拉，低有效键需外部上拉）。WiFi+蓝牙固件约 1.5MB，分区表已改 4MB Flash + factory 3MB（`partitions.csv`），从 2MB 配置升级首次烧录前建议 `idf.py erase-flash`。

## HAL 层功能记录

### hal_uart（UART 驱动，封装 ESP-IDF uart 事件队列驱动）

| 功能 | API | 说明 |
|------|-----|------|
| 串口初始化 | `HalUartInit()` | 帧格式经 `HalUartConfig_S` 可配置（波特率/数据位 5~8/校验无偶奇/停止位 1、1.5、2/流控 RTS、CTS 及引脚）；0 值字段取默认 8N1 无流控；装驱动（RX 环形缓冲 256B + 事件队列 20 深）+ 每串口接收分发任务（栈 3072B，优先级 5） |
| 串口反初始化 | `HalUartDeinit()` | 删任务、卸驱动、释放缓冲 |
| 运行时改波特率 | `HalUartSetBaud()` | 不重初始化直接更新指定串口波特率 |
| 阻塞发送 | `HalUartSend()` | 无 TX 环形缓冲直写 FIFO，`TimeoutMs` 约束等待发送完成 |
| 读取数据 | `HalUartRead()` | 从驱动环形缓冲读取，超时 0 = 立即返回已有数据 |
| 查询可读字节数 | `HalUartRxCountGet()` | 轮询场景使用 |
| 清空接收 | `HalUartRxClear()` | 清缓冲 + 复位事件队列 |
| 事件回调注册 | `HalUartSetCallback()` | 全串口共用回调按 Port 区分；事件在接收任务上下文上抛（非中断） |

事件链：`uart 驱动 ISR（ESP-IDF 内部 FromISR 入队）→ 每串口接收任务 → 回调（RX / RX_OVF / RX_FULL）`。帧间隔超时 3 符号时间触发 RX 事件。

### hal_led（LED GPIO 驱动，封装 ESP-IDF gpio 驱动）

| 功能 | API | 说明 |
|------|-----|------|
| LED 初始化 | `HalLedInit()` | 按引脚表（`hal_led.c` 内 `G_LedPinTable`）配置推挽输出并默认熄灭，可重复调用 |
| LED 状态控制 | `HalLedCtrl()` | 点亮/熄灭/翻转（TOGGLE 经电平缓存取反），`HalLed_E` 编号寻址 |

> 引脚映射集中在 `hal_led.c` 的 `G_LedPinTable`（HAL_LED_1 → GPIO2）；上层经 `HalLed_E` 枚举访问，不感知 GPIO 编号。

### hal_key（按键 GPIO 驱动，封装 ESP-IDF gpio 驱动）

| 功能 | API | 说明 |
|------|-----|------|
| 绑定任意 GPIO 为按键 | `HalKeyBind()` | 指定按键编号（`HalKey_E` 槽位）+ 任意 GPIO（0~39）+ 有效电平（低/高）；配置为输入并按有效电平使能内部上/下拉；GPIO6~11（模组 Flash）黑名单拒绝，GPIO34~39 无内部上下拉（低有效需外部上拉）；重复绑定覆盖旧绑定 |
| 读取按键电平 | `HalKeyRead()` | 非阻塞直读输入电平与有效电平比对，1=按下 / 0=松开 / -1=未绑定或参数非法；无消抖（消抖由 BSP 状态机完成） |

> 按键槽位（HAL_KEY_1~4）与 GPIO 编号完全解耦，运行时经 `HalKeyBind` 绑定任意 GPIO；上层经槽位编号访问，不感知 GPIO。

### hal_wifi（WiFi 驱动，封装 ESP-IDF esp_wifi/netif/nvs_flash，AP+STA 双模）

| 功能 | API | 说明 |
|------|-----|------|
| WiFi 初始化 | `HalWifiInit()` | 初始化 NVS/netif/esp_wifi 并启动 SoftAP+STA 双模：SoftAP 常开供配网，STA 用于连接路由器；热点配置经 `HalWifiApConfig_S`（SSID/密码/信道 1~13/最大接入 1~4），密码空串=开放热点，0 值字段取默认（信道 1 / 接入 2） |
| STA 凭据保存 | `HalWifiStaConfigSave()` | SSID/密码写入 NVS（命名空间 `wifi`，键 `ssid`/`pwd`）持久化，掉电不丢 |
| STA 凭据读取 | `HalWifiStaConfigLoad()` | 从 NVS 读回凭据（自动截断至缓冲尺寸），供上层展示/回填 |
| STA 发起连接 | `HalWifiStaConnect()` | 从 NVS 读凭据写入 STA 配置并连接（无凭据返回失败）；断开后可再次调用重试 |
| STA 断开 | `HalWifiStaDisconnect()` | 主动断开当前连接 |
| STA 状态查询 | `HalWifiStaStateGet()` | 返回 IDLE（无凭据/未连接）/ CONNECTING（连接中）/ CONNECTED（已获 IP） |
| STA IP 查询 | `HalWifiStaIpGet()` | 输出点分十进制 IP 字符串（含结束符最长 16B） |
| SoftAP NAT 中继 | 无新增 API（事件内自动启停） | STA 联网即开 NAPT：热点客户端报文改写源地址借道 STA 上网 + DHCP 下发 DNS（优先上游网关，退回 223.5.5.5）；STA 断开自动关闭、重连自动恢复 |
| 周边热点扫描 | `HalWifiScanGet()` | 阻塞式全信道扫描（约 1.5~3s），按 RSSI 降序同名去重，最多 20 条（SSID/信号强度/是否加密）；扫描期间 SoftAP 信标短暂停发属正常 |
| 事件回调注册 | `HalWifiSetCallback()` | GOT_IP / DISCONNECTED 事件上抛（运行于 ESP-IDF 事件任务上下文） |

事件链：`esp_wifi 驱动 → ESP-IDF 事件循环任务 → 事件回调（GOT_IP / DISCONNECTED）→ BSP 转发 APP`。STA 关联参数：认证门槛取 `WIFI_AUTH_OPEN`（任意认证模式可关联）+ PMF capable（兼容 WPA3/混合网络）。

> **NAPT 热点中继**（sdkconfig：`LWIP_IP_FORWARD` + `LWIP_IPV4_NAPT`）：STA 联网即自动开启 —— 热点客户端（192.168.4.x）经 NAPT 改写源地址借道 STA 上网，DNS 由 DHCP 下发（优先上游网关，无效退回 223.5.5.5）；STA 断开自动关闭、重连自动恢复。单射频半双工中继，预期带宽 10~20Mbps，高清视频可能缓冲。

### hal_http（HTTP/WebSocket 服务器驱动，封装 ESP-IDF esp_http_server）

| 功能 | API | 说明 |
|------|-----|------|
| 服务器初始化 | `HalHttpInit()` | 启动 HTTP 服务器（端口 80，最大并发 socket 7），含 WebSocket 支持 |
| URI 注册 | `HalHttpUriRegister()` | 按 `HalHttpUri_S` 注册路径（如 `/`、`/wifi`、`/ws`）+ 方法（GET/POST/WS）+ 处理回调；配置须长期保活（建议常量/静态存储） |
| 请求体长度 | `HalHttpReqContentLen()` | POST 请求体长度（字节） |
| 请求体接收 | `HalHttpReqContentRecv()` | 读 POST 请求体到调用方缓冲（表单解析用） |
| 请求应答 | `HalHttpReqRespond()` | 按 HTTP 状态码/Content-Type/响应体回复，支持重定向（配网提交后跳转） |
| WebSocket 收帧 | `HalHttpReqWsRecv()` | 读一帧 WS 数据到缓冲，返回 0=握手阶段（仅触发 WS_OPEN 上抛）；超长帧（>512B）自动丢弃不阻塞 |
| WebSocket 推送 | `HalHttpWsPush()` | 经服务器工作队列**异步**向指定 fd 推二进制帧，任意任务上下文可安全调用 |
| WebSocket 文本推送 | `HalHttpWsPushText()` | 同上，推文本帧（JSON 状态用） |

> `HalHttpReq_S` 的 `pRaw` 为厂商请求句柄占位，上层保持 opaque 仅回传本层；WS 推送走 `httpd` 工作队列异步通道，与 WS 收帧（服务器任务上下文）解耦。

### hal_spp（经典蓝牙 SPP 驱动，封装 ESP-IDF Bluedroid SPP，服务端模式）

| 功能 | API | 说明 |
|------|-----|------|
| SPP 初始化 | `HalSppInit()` | 初始化 BT 控制器（CLASSIC_BT）+ Bluedroid 协议栈 + SPP 增强模式，并以服务端身份启动 SPP 服务（异步，INIT 事件内拉起）被动等待客户端接入；入参设备名/服务名 |
| SPP 发送 | `HalSppSend()` | 向已连接客户端发数据；未连接返回 -2，链路拥塞（CONG）返回 -3 暂缓重发 |
| 连接状态查询 | `HalSppIsConnected()` | 1=已连接 / 0=未连接 |
| 事件回调注册 | `HalSppSetCallback()` | OPENED / CLOSED / DATA 事件上抛（运行于 Bluedroid 事件任务上下文） |

事件链：`BT 控制器 → Bluedroid 事件任务 → SPP 回调（OPENED/CLOSED/DATA）→ BSP 转发 APP`；单连接模型，新客户端接入自动接管旧连接。

## BSP 层功能记录

### bsp_uart（板载串口封装：覆盖全部 3 路硬件串口）

| 功能 | API | 说明 |
|------|-----|------|
| 板载串口初始化 | `BspUartInit()` | 按 `bsp_uart.h` 使能宏（`BSP_UART_DBG_EN`/`BSP_UART_EXT_EN`/`BSP_UART_COMM_EN`）逐路初始化 DBG（UART0）/EXT（UART1）/COMM（UART2），波特率/引脚集中在 `bsp_uart.h` 配置，帧格式默认 8N1；先挂事件转发再逐路 Init，某路失败不阻断其余路 |
| 板载串口反初始化 | `BspUartDeinit()` | 指定路转调 `HalUartDeinit()`，卸驱动释放资源 |
| 运行时改波特率 | `BspUartSetBaud()` | 指定路转调 `HalUartSetBaud()`，不重初始化 |
| 语义串口发送 | `BspUartSend()` | `BspUart_E` 语义号（DBG/EXT/COMM）经映射表转发对应硬件串口 |
| 语义串口读取 | `BspUartRead()` | 同上 |
| 查询可读字节数 | `BspUartRxCountGet()` | 同上 |
| 清空接收 | `BspUartRxClear()` | 指定路清接收缓冲 + 复位事件队列 |
| 事件回调注册 | `BspUartSetCallback()` | 接收 HAL 事件（反查映射表）转为带 Port 号的板级语义事件转发 APP |

### bsp_led（板载灯封装）

| 功能 | API | 说明 |
|------|-----|------|
| 板载灯初始化 | `BspLedInit()` | 转调 HAL LED 初始化 |
| 板载灯设置 | `BspLedSet()` | 语义灯号/状态（`BspLed_E`/`BspLedState_E`）→ HAL 硬件灯号映射输出 |

> 语义映射集中在 `bsp_led.c`：`BSP_LED_RUN`（运行灯）→ `HAL_LED_1`（GPIO2 板载灯）。LED 为 GPIO 直控器件，无 DRV 层（第 2 节注）。

### bsp_key（按键消抖扫描状态机：按住/按下/松开/单击/双击/长按/连发事件识别）

| 功能 | API | 说明 |
|------|-----|------|
| 按键模块初始化 | `BspKeyInit()` | 复位全部按键状态机，清空绑定与事件标志 |
| 绑定任意 GPIO 为按键 | `BspKeyBind()` | 转调 `HalKeyBind` 并复位该键状态机；返回 0 成功 / -1 参数 / -2 裁剪 / -3 HAL 失败 |
| 扫描状态机 | `BspKeyTick()` | 须由 APP 以 10ms（`BSP_KEY_TICK_PERIOD_MS`）周期调用；内部 20ms（`BSP_KEY_SCAN_PERIOD_MS`）消抖采样，事件识别方式与 Doc/drv_key 标志位状态机一致；未绑定按键自动跳过 |
| 查询消费按键事件 | `BspKeyCheck()` | 传入事件标志（`BSP_KEY_HOLD/DOWN/UP/SINGLE/DOUBLE/LONG/REPEAT`，可按位或）查询，命中返回 1 并清除已消费标志（HOLD 为电平态不清除）；0 未命中 |
| 长按阈值配置 | `BspKeyTimeLongSet()` | 运行时修改长按判定时间（默认 3000ms，双击窗口 50ms / 连发周期 100ms 在 `bsp_key.h` 宏配置） |

> 按键为 GPIO 直控器件，无 DRV 层（第 2 节注），BSP 直达 HAL；状态机移植自 Doc/drv_key（0~4 态：空闲→按下→双击窗口→双击松开→长按连发），事件标志 0x01~0x40 与参考实现一致。

### bsp_wifi（板载 WiFi 封装：配网热点参数 + 自动重连组织）

| 功能 | API | 说明 |
|------|-----|------|
| WiFi 模块初始化 | `BspWifiInit()` | 以 `bsp_wifi.h` 集中定义的热点参数（SSID `ESP32_Config`/密码 `12345678`/信道 6/接入 2）初始化 AP+STA 双模；NVS 有凭据则自动发起 STA 连接 |
| 配网凭据下发 | `BspWifiConfigSet()` | 保存 SSID/密码到 NVS 并连接（网页表单提交路径）；IDLE 态直接发起，连接中/已连接态先断开、由断开事件回调自动以新凭据重连（规避 disconnect 未完成即 connect 的状态冲突） |
| 当前 SSID 查询 | `BspWifiConfigSsidGet()` | 从 NVS 读回已配网 SSID（状态栏展示用） |
| 周边热点扫描 | `BspWifiScanGet()` | 转发 HAL 扫描（阻塞 1.5~3s，最多 20 条）；扫描期间挂起自动重连（扫描与关联互斥），扫描结束恢复连接尝试 |
| STA 状态查询 | `BspWifiStaStateGet()` | IDLE / CONNECTING / CONNECTED 板级语义 |
| STA IP 查询 | `BspWifiStaIpGet()` | 点分十进制 IP 字符串 |
| 事件回调注册 | `BspWifiSetCallback()` | GOT_IP / DISCONNECTED 事件转发 APP；**断线时本层自动重连**（DISCONNECTED 事件内重发 `HalWifiStaConnect`，重试上限 `BSP_WIFI_RETRY_MAX`=20 次防密码错误死循环，GOT_IP 清零计数） |

> WiFi 为片上外设，无 DRV 层（第 2 节注），BSP 直达 HAL；热点参数集中在 `bsp_wifi.h`，换板改此处。

### bsp_web（板载网页封装：内置配网页 + 网页串口工具 + WebSocket 通道）

| 功能 | API | 说明 |
|------|-----|------|
| 网页模块初始化 | `BspWebInit()` | 启动 HTTP 服务器并注册 5 个 URI：`/`（GET 配网页+串口工具单页）、`/wifi`（POST 配网表单）、`/scan`（GET 周边热点扫描 JSON 列表）、`/baud`（POST 波特率设置）、`/ws`（WebSocket 数据通道）；页面 HTML/JS 内置于固件，无外部资源 |
| 事件回调注册 | `BspWebSetCallback()` | 上抛 4 类事件：WS_OPEN（新连接，应推状态）/ WS_DATA（网页串口工具发来数据）/ WIFI_SAVE（配网表单，数据格式 `ssid\npwd`）/ BAUD_SET（波特率数字串）；回调运行于 HTTP 服务器任务上下文 |
| WS 二进制广播 | `BspWebWsBroadcast()` | 向全部已连接网页串口工具推二进制帧（串口数据透传路径），失败连接自动跳过 |
| WS 文本广播 | `BspWebWsBroadcastText()` | 同上推文本帧（JSON 状态推送用） |

> 内置页面含配网表单与串口工具（波特率下拉 300~500000 / HEX 显示 / HEX 发送 / CRLF 选项 / 自动滚动），JS 侧经 `TextEncoder`/`TextDecoder` 处理二进制；表单提交经 URL 解码（`%XX` 与 `+`）后拆字段。

### bsp_bt（板载蓝牙封装：经典蓝牙 SPP 透传通道）

| 功能 | API | 说明 |
|------|-----|------|
| 蓝牙模块初始化 | `BspBtInit()` | 以 `bsp_bt.h` 集中定义的设备名 `ESP32-UART` / 服务名 `ESP32_SPP` 启动 SPP 服务端，等待手机/电脑蓝牙串口客户端接入 |
| SPP 发送 | `BspBtSppSend()` | 向已连接客户端透传数据 |
| 连接状态查询 | `BspBtSppIsConnected()` | 1=已连接 / 0=未连接 |
| 事件回调注册 | `BspBtSetCallback()` | OPENED / CLOSED / DATA 事件转发 APP（DATA 数据仅回调期间有效） |

> 蓝牙为片上外设，无 DRV 层（第 2 节注），BSP 直达 HAL；与 WiFi 共存依赖 `CONFIG_ESP_COEX_SW_COEXIST_ENABLE` 软件共存。

## APP 层功能记录

### app_uart（串口回显业务）

| 功能 | API | 说明 |
|------|-----|------|
| 业务初始化 | `AppUartInit()` | 注册回调 + 初始化板载串口（`BspUartInit` 按使能宏逐路），回显业务挂 COMM 口；`CFG_APP_NET_EN=1` 时通信口回调在 `AppNetInit` 末尾被 app_net 接管（本业务退化为 EXT/DBG 口可用） |
| 事件处理 | `AppUartEventHandler()`（内部） | RX/RX_FULL 事件读取数据原样回发，单帧超 128B 分批搬运 |
| 业务发送 | `AppUartSend()` | 对外上报/应答统一出口（转 BSP 通信口） |

### app_led（LED 闪烁策略）

| 功能 | API | 说明 |
|------|-----|------|
| 业务初始化 | `AppLedInit()` | 转调 BSP 板载灯初始化 |
| 闪烁策略处理 | `AppLedBlinkProcess()` | 运行灯 1Hz 心跳（500ms 翻转一次），按主循环调度周期累加节拍 |

### app_key（按键事件消费业务）

| 功能 | API | 说明 |
|------|-----|------|
| 业务初始化 | `AppKeyInit()` | 初始化 BSP 按键模块并按 `app_key.c` 顶部宏（`APP_KEY_1_GPIO_NUM`/`APP_KEY_1_ACTIVE_LOW`）绑定默认按键（BSP_KEY_1 → GPIO0 BOOT 键，低有效）；换绑任意 GPIO 只改该宏；绑定失败打印告警不阻断启动 |
| 扫描驱动与事件消费 | `AppKeyProcess()` | 先驱动 `BspKeyTick()` 扫描状态机，再消费事件：单击翻转运行灯 + 打印，双击/长按/连发打印事件名（演示用，用户在此挂自己的业务） |

### app_net（网络业务：WiFi 配网 + 网页串口工具 + 蓝牙 SPP 转发数据路由）

| 功能 | API | 说明 |
|------|-----|------|
| 业务初始化 | `AppNetInit()` | 依次拉起 bsp_wifi → bsp_web → bsp_bt 并注册三类回调（WiFi 事件/网页事件/蓝牙事件）；末尾接管 UART2 回调（覆盖 app_uart 回显，通信口数据改走网络路由） |
| 周期处理 | `AppNetProcess()` | 1Hz 状态推送：向全部网页串口工具广播 JSON `{"ssid":"...","ip":"...","spp":0/1}`（当前 SSID / IP / 蓝牙连接态） |

**数据路由规则**（本模块为四条业务通路的中枢）：

| 输入事件 | 路由动作 |
|---------|---------|
| UART2 RX（外部串口设备→ESP32） | 同步双路转发：① WS 广播到全部网页串口工具；② SPP 发给已连接蓝牙客户端（256B 分批） |
| WS_DATA（网页串口工具发送） | 写 UART2 TX（数据到达外部串口设备） |
| BT DATA（蓝牙客户端发送） | 写 UART2 TX（数据到达外部串口设备） |
| WIFI_SAVE（配网表单提交） | 拆分 `ssid\npwd` 调 `BspWifiConfigSet` 保存并连接 |
| BAUD_SET（网页设置波特率） | `strtoul` 解析并校验 300~500000 后调 `BspUartSetBaud`（UART2 在线改波特率） |
| WS_OPEN（新网页连接） | 立即推送一次状态 JSON（页面状态栏即连即显） |

> WS 与蓝牙之间不互转（两者均为"远端"，仅与 UART2 互通），避免数据回环。

### app_main（应用入口与主调度）

| 功能 | API | 说明 |
|------|-----|------|
| 启动调度 | `app_main()` | 打印横幅 → 初始化业务模块（按开关宏裁剪，app_net 网络业务最后初始化：蓝牙协议栈装载阻塞数秒属正常）→ 主循环按 `APP_MAIN_PROCESS_PERIOD_MS`（10ms）周期轮询各业务槽 |
| 调度周期 | `APP_MAIN_PROCESS_PERIOD_MS` 宏 | 主循环节拍（10ms），各业务 Process 须非阻塞 |

## 硬件号数据流转

**数据通路清单表**：

| 通路 | ①输入源 | ②采集/解析 | 触发·频率 | ③数据落点 | ④消费方 | ⑤输出 |
|------|---------|-----------|----------|----------|---------|-------|
| P1 通信串口 | 外部设备/PC 终端 → UART2 RX（GPIO16） | esp-idf uart 驱动 ISR + hal_uart 接收任务事件分发 | 中断触发（帧间隔超时 3 符号 / 缓冲阈值） | uart 驱动 RX 环形缓冲 256B | app_uart 回显处理（回调上下文） | bsp_uart → hal_uart → UART2 TX（GPIO17）原样回发 |
| P2 运行灯 | 调度节拍（app_main 主循环 10ms） | app_led 闪烁策略（500ms 到期翻转） | 1Hz 槽（主循环轮询，非阻塞） | G_BlinkTick 节拍累加器 | app_led 闪烁策略 | bsp_led → hal_led → GPIO2 板载灯亮灭 |
| P3 按键 | BOOT 键按下/松开（GPIO0 电平变化） | bsp_key 扫描状态机（`BspKeyTick` 主循环 10ms 驱动，20ms 消抖采样，识别单击/双击/长按/连发） | 轮询槽（主循环轮询，非阻塞） | G_KeyFlag 每键事件标志（0x01~0x40 位图） | app_key 事件消费（`BspKeyCheck` 消费型读取） | 单击 → bsp_led → hal_led 翻转 GPIO2 运行灯 + UART0 日志打印事件 |
| P4 WiFi 配网 | 手机/电脑连接热点 `ESP32_Config` → 浏览器提交表单（POST /wifi） | hal_http 服务器任务 + bsp_web 表单解析（URL 解码 + 字段拆分 `ssid\npwd`） | 浏览器请求触发 | 事件回调参数（栈上透传） | app_net 配网处理（`BspWifiConfigSet`） | bsp_wifi → hal_wifi → NVS 持久化 + STA 连接路由器；页面重定向回首页 |
| P5 串口→网页 | 外部串口设备 → UART2 RX（GPIO16） | esp-idf uart 驱动 ISR + hal_uart 接收任务事件分发 | 中断触发（帧间隔超时 3 符号） | uart 驱动 RX 环形缓冲 256B | app_net 串口路由（256B 分批） | ① bsp_web WS 广播 → hal_http 异步推送 → 浏览器串口工具显示；② bsp_bt → hal_spp → 蓝牙客户端 |
| P6 网页→串口 | 浏览器串口工具发送（WS /ws 帧） | hal_http WS 收帧 + bsp_web 事件上抛 | 浏览器发送触发 | 事件回调参数（仅回调期间有效） | app_net 网页路由 | bsp_uart → hal_uart → UART2 TX（GPIO17）到达外部串口设备 |
| P7 蓝牙→串口 | 手机/电脑蓝牙串口客户端发送（SPP） | hal_spp Bluedroid 事件任务 + bsp_bt 事件转发 | 蓝牙接收触发 | 事件回调参数（仅回调期间有效） | app_net 蓝牙路由 | bsp_uart → hal_uart → UART2 TX（GPIO17）到达外部串口设备 |

**分阶段流程图**：

```mermaid
flowchart LR
    subgraph S1[①输入源]
        A1[PC串口终端/外部设备<br>UART2 RX GPIO16]
        A2[app_main主循环节拍<br>10ms调度槽]
        A3[BOOT键按下/松开<br>GPIO0电平变化]
        A4[手机/电脑浏览器<br>WiFi配网表单提交]
        A5[浏览器串口工具<br>WebSocket发送]
        A6[蓝牙串口客户端<br>SPP发送]
    end
    subgraph S2[②采集/解析]
        B1[esp-idf uart驱动 ISR<br>FromISR入队]
        B2[hal_uart接收任务<br>事件分发+回调上抛]
        B2x[app_led闪烁策略<br>500ms翻转]
        B3[bsp_key扫描状态机<br>10ms驱动20ms消抖采样]
        B4[hal_http服务器任务<br>bsp_web表单解析/WS收帧]
        B5[hal_spp Bluedroid事件<br>bsp_bt事件转发]
    end
    subgraph S3[③数据缓存/命令]
        C1[uart驱动RX环形缓冲<br>256B]
        C2[G_BlinkTick<br>节拍累加器]
        C3[G_KeyFlag事件标志位图<br>单击/双击/长按/连发]
        C4[NVS wifi命名空间<br>ssid/pwd持久化]
    end
    subgraph S4[④决策]
        D1[app_uart回显处理<br>超128B分批搬运]
        D2[运行灯TOGGLE命令<br>BSP_LED_RUN]
        D3[app_key事件消费<br>BspKeyCheck读后清除]
        D4[app_net数据路由<br>UART2↔WS/SPP双向互通]
    end
    subgraph S5[⑤输出]
        E1[bsp_uart→hal_uart<br>阻塞发送]
        E2[UART2 TX GPIO17<br>回显数据/网页蓝牙下发]
        E3[bsp_led→hal_led<br>GPIO电平输出]
        E4[GPIO2板载LED<br>1Hz心跳/按键翻转]
        E5[bsp_web→hal_http<br>WS异步广播]
        E6[bsp_bt→hal_spp<br>SPP透传发送]
        E7[浏览器串口工具显示<br>手机/电脑蓝牙接收]
    end
    A1 -.中断直达.-> B1
    B1 -.事件队列.-> B2
    B1 --> C1
    B2 -->|回调 P1:RX事件+Len| D1
    D1 -->|BspUartRead 0超时| C1
    D1 --> E1 --> E2
    A2 -->|P2:10ms轮询| B2x --> C2
    C2 -->|P2:500ms到期| D2 --> E3 --> E4
    A2 -->|P3:10ms轮询| B3
    A3 -->|20ms消抖采样| B3 --> C3
    C3 -->|P3:命中事件| D3
    D3 -->|单击| E3
    D3 -->|UART0日志打印| E2
    A4 -->|P4:POST /wifi| B4
    B4 -->|P4:WIFI_SAVE事件| D4
    D4 -->|P4:保存凭据| C4
    B2 -->|P5:RX事件+Len| D4
    D4 -->|P5:串口数据| E5 --> E7
    D4 -->|P5:串口数据| E6 --> E7
    A5 -->|P6:WS /ws帧| B4
    B4 -->|P6:WS_DATA事件| D4
    D4 -->|P6:下发数据| E1
    A6 -->|P7:SPP数据| B5
    B5 -->|P7:BT DATA事件| D4
    D4 -->|P7:下发数据| E1
```

> 虚线 `-.->` = 中断直达；实线 `-->` = 任务上下文阻塞/轮询。日志通路（UART0）为系统通路，不计入特性表。

## 构建与烧录

```powershell
# VS Code ESP-IDF 扩展：配置扩展指向 ESP-IDF 安装目录后，用底部状态栏 Build/Flash/Monitor
# 命令行（每个新终端先激活环境）：
cd <ESP-IDF安装目录>; .\export.bat
cd f:\00.Code\11ESP\ESP-32
idf.py set-target esp32      # 首次（生成 sdkconfig；sdkconfig.defaults 已指定 esp32，亦可直接 build）
idf.py build
idf.py -p COMx flash monitor # COMx 换实际串口号，退出监视 Ctrl+]
idf.py size                  # 资源占用检查（结果回填 Project_Level_Skill.md 13.4 节）
```

## 功能验证（回显 Demo）

1. USB-TTL 模块：TX→GPIO16，RX→GPIO17，GND 共地（注意**不要**接模组 GPIO1/3，那是日志/下载口）
2. PC 串口助手打开 USB-TTL 对应串口，115200-8N1
3. 烧录后日志口（UART0，板载 USB 转串口，115200）打印 `[app_uart] comm port ready`
4. 串口助手发送任意字符串（≤128B 一次回完，更长分批），收到相同内容即通路正常

## 功能验证（按键 Demo）

1. 无需接线：默认按键绑定 DevKitC 板载 BOOT 键（GPIO0，低有效）
2. **单击** BOOT 键：GPIO2 运行灯翻转，日志口打印 `[app_key] key1 single: toggle led`
3. **双击**（间隔 <50ms+50ms 窗口）：打印 `[app_key] key1 double`
4. **长按** ≥3s：打印 `[app_key] key1 long`，继续按住每 100ms 打印 `[app_key] key1 repeat`
5. 换绑任意 GPIO：改 `app_key.c` 顶部 `APP_KEY_1_GPIO_NUM` 宏（或运行时调 `BspKeyBind`），注意 GPIO6~11 黑名单与 GPIO34~39 无内部上下拉约束

## 功能验证（WiFi 配网 / 网页串口 / 蓝牙 Demo）

**准备**：USB-TTL 模块 TX→GPIO16 / RX→GPIO17 / GND 共地（同回显 Demo 接线）；烧录后热点 `ESP32_Config`（密码 `12345678`）自动开启，日志口打印 `[app_net] ...` 系列。

**① WiFi 网页配网（扫描列表选择）**：

1. 手机/电脑连接热点 `ESP32_Config`
2. 浏览器访问 `http://192.168.4.1`，打开内置页面（配网表单 + 串口工具）
3. 点击 **Scan** 扫描周边热点（约 2~3s，状态栏显示 scanning）→ 下拉列表按信号强度列出热点（`[+]`=加密 / `[O]`=开放，ESP32 仅支持 2.4GHz，列表即 2.4G 可连网络）
4. 下拉选择家里的路由器（SSID 自动填入）→ 输入密码 → 点 **Save & Connect** → 日志打印连接过程，成功后状态栏显示 SSID/IP
5. 重启 ESP32 验证凭据持久化：日志自动打印已保存的 SSID 并连接（无需再次配网）

> 注：密码错误时重试 20 次后停止自动重连（防死循环），重新提交正确密码即可；SSID 也可不经扫描直接手动输入。

**② 网页串口工具收发**：

1. 页面打开后即自动建立 WebSocket 连接，顶部状态栏显示当前 SSID/IP/蓝牙状态（1Hz 刷新）
2. PC 串口助手（115200-8N1）向 UART2 发送任意数据 → 网页串口工具接收区实时显示（可勾选 HEX 显示）
3. 网页发送区输入内容点发送（可选 HEX 发送/追加 CRLF）→ 串口助手收到相同内容
4. 波特率下拉选择新波特率（300~500000）→ 页面与串口助手同步改波特率后仍可互通

**③ 蓝牙 SPP 透传**：

1. 手机安装蓝牙串口 App（如 Serial Bluetooth Terminal），搜索并连接 `ESP32-UART`
2. 日志打印 `[bsp_bt] spp opened`，网页状态栏 `spp:1`
3. 串口助手向 UART2 发数据 → 手机蓝牙串口 App 收到（串口→蓝牙转发）
4. 手机 App 发数据 → 串口助手收到（蓝牙→串口转发）
5. 三端同时在线验证：串口助手发一条数据，网页串口工具与手机 App **同时**收到

**④ 热点上网（NAT 中继）**：

1. 前提：① 配网完成且日志已打印 `[app_net] wifi connected`（NAPT 自动开启，日志见 `[hal_wifi] nat on: ap clients online via sta (dns ...)`）
2. 手机**关闭移动数据**，连接热点 `ESP32_Config`；若此前连过须先“忘记此网络”再连（重新获取 DHCP 下发的 DNS）
3. 浏览器打开任意网站应正常加载；短视频 App 可正常刷（单射频中继，预期 10~20Mbps，高清可能缓冲）
4. STA 断网（如关路由器）：热点与 192.168.4.1 配网页仍可用，仅外网断开；路由恢复后 NAPT 自动重开

## MCU 移植提示

更换 MCU（如 ESP32-S3/C3）仅需重写 `hal_uart.c` / `hal_led.c` / `hal_key.c` 内部实现（接口签名不变）+ 调整 `bsp_uart.h` / `hal_led.c` 引脚映射（`hal_key` 无引脚表，任意 GPIO 运行时绑定）；上层 BSP/APP 零改动（见 Project_Level_Skill.md 第 10 节）。

网络功能同理：更换带 WiFi/BT 的其他 ESP 型号重写 `hal_wifi.c` / `hal_http.c` / `hal_spp.c` 内部实现（接口签名不变）；无 WiFi/BT 的 MCU 将 `cfg_modules.h` 对应 `CFG_HAL_*`/`CFG_BSP_*`/`CFG_APP_NET_EN` 置 0，全部模块自动降级为空实现，其余业务不受影响。
