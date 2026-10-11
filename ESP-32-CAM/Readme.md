# ESP32-CAM 网页视频监控工程功能记录

- **板卡**：AI-Thinker ESP32-CAM（SoC：ESP32-D0WDQ6，双核 Xtensa LX6 @ 240MHz，4MB Flash / **实测板载 8MB PSRAM**——经典 ESP32 最多映射 4MB）
- **传感器**：**OV3660**（实测 PID=0x3660，标称 OV2640 的板子实际装了 OV3660，驱动自动识别；UXGA 上限，QXGA 不启用）
- **SDK**：ESP-IDF **v6.1**（本机激活脚本 `F:\00.Code\11ESP\idf-env.bat`）；摄像头驱动 **esp32-camera 2.1.8**（组件仓库自动拉取，`main/idf_component.yml` 声明）
- **版本号规则**：同 ESP-32 工程（V主.次.大功能.小功能）；当前 **V1.3.0.0**（人体检测+人流量）
- **代码仓**：`https://gitee.com/YYM642443594/ESP.git` 分支 `feature/ESP32-Camer`（串口透传工程见 develop 分支）；架构/分层规范同 ESP-32 工程（APP→BSP→HAL→ESP-IDF，见仓库 `Project_Level_Skill.md`）
- **网页端**：暗色单页四标签（配网/视频监控/GPIO 控制/存储），配网栈与网页谱系移植自 develop 分支（ESP8266-develop 参照）

## 硬件资源占用表

| 外设 | 引脚/资源 | 用途 | 归属模块 |
|------|-----------|------|----------|
| 摄像头 DVP | XCLK=0, SIOD=26, SIOC=27, Y2=5, Y3=18, Y4=19, Y5=21, Y6=36, Y7=39, Y8=34, Y9=35, VSYNC=25, HREF=23, PCLK=22, PWDN=32 | OV3660 并口（固定接线） | hal_cam |
| SD 卡槽 | CLK=14, CMD=15, D0=2（**1-bit 模式**；D1=4 留补光灯/D2=12/D3=13 留 GPIO） | 抓拍存储 FATFS `/sdcard` | bsp_sd |
| 补光灯 | GPIO4（与 SD D1 复用，1-bit 模式下归补光灯） | 板载高亮 LED | hal_cam |
| 板载红色 LED | GPIO33 | GPIO 控制页可控 | hal_gpio/bsp_gpio |
| 剩余可控 GPIO | 1/3（UART0 日志口，控制后串口失联）、2/4/12/13/14/15/33 | 网页 GPIO 控制页 | bsp_gpio |
| 不可用 | GPIO0=摄像头 XCLK；GPIO16/17=PSRAM；GPIO6~11=Flash；GPIO34~39 仅输入且被摄像头占用 | — | — |
| WiFi | SoftAP `ESP32_Config`/192.168.4.1 + STA；NAPT 借道上网 | 配网/监控/NAT 中继 | hal_wifi/bsp_wifi |
| 下载口 | **COM9**（CH340，**必须 115200**——460800 连接后失联） | 烧录/日志 | — |

## HAL 层功能记录

### hal_cam（摄像头驱动，封装 esp32-camera）

| 功能 | API | 说明 |
|------|-----|------|
| 初始化 | `HalCamInit(pCfg)` | **帧缓冲始终按最大档 UXGA + 显式 `jpeg_buffer_size`=960KB×2 分配**（PSRAM），用户档位（分辨率/质量/镜像/翻转）init 后经传感器接口应用；PSRAM 缺失降级 DRAM+QVGA |
| 取帧/归还 | `HalCamFbGet(ppJpg,pLen,TimeoutMs)` / `HalCamFbReturn(pFb)` | 2.1.x `esp_camera_fb_get()` **无参**（驱动内部固定 4s 超时），帧句柄 void* 透传归还 |
| 参数设置 | `HalCamSizeSet/QualitySet/HmirrorSet/VflipSet` | 运行时可切，流传输中生效于后续帧；档位枚举 QVGA~UXGA 板级映射 |
| 状态查询 | `HalCamSizeGet/QualityGet/HmirrorGet/VflipGet/SensorNameGet/PsramFreeGet` | 传感器状态回读，状态 JSON 用 |
| 补光灯 | `HalCamFlashLedSet/Get` | GPIO4 推挽输出，上电默认灭 |

### hal_wifi（WiFi 驱动，APSTA 双模 + NAPT，develop 移植 + NAT 回迁）

同 ESP-32 工程 hal_wifi（NVS 凭据/扫描/事件回调全套），差异：本工程 V1.1.0.0 回迁了完整 **NAPT 借道上网**（GOT_IP → `ip_napt_enable` + 上游 DNS 写入 AP DHCP + 8s 后踢全部 AP 客户端强制重取含正确 DNS 的租约；断开自动关 NAPT）。`CONFIG_LWIP_IP_FORWARD`+`CONFIG_LWIP_IPV4_NAPT` 必须写 `sdkconfig.defaults`。

### hal_http（HTTP 服务器，双实例 + 流式 API）

| 功能 | API | 说明 |
|------|-----|------|
| 双实例启动 | `HalHttpInit()` | 80 主实例（页面+/api+快照+SD 下载，4 连接，**max_uri_handlers=20**，**uri_match_fn=httpd_uri_match_wildcard**）；81 流实例（MJPEG 专用，3 连接，send_wait_timeout=2s，ctrl_port=32769） |
| URI 注册 | `HalHttpUriRegister(pUriCfg)` | `HalHttpUri_S` 含 `StreamIns` 字段路由到流实例 |
| 请求处理 | `HalHttpReqContentLen/Recv/Respond/UriGet` | 通用 GET/POST 应答；UriGet 供通配路由解析路径 |
| 流式响应 | `HalHttpStreamOpen(pReq,pBoundary)` / `HalHttpStreamSend(pReq,pBuf,Len)` | multipart 响应头 + socket 原始 send（连续 3 次 SO_SNDTIMEO 超时全零发才判死，瞬时慢客户端不断流） |

### hal_gpio（通用 GPIO 驱动）

`HalGpioSetup(Num,Mode,Level)`：输入浮空/上拉/下拉/推挽输出；GPIO6~11 Flash 黑名单拒绝，34~39 仅允许输入浮空。`HalGpioRead` 实时电平回读（输入/输出均可读）。

## BSP 层功能记录

| 模块 | 关键点 |
|------|--------|
| bsp_cam | NVS（命名空间 cam）持久化 fsz/jq/hm/vf 四键；帧率统计（两次查询差折算，页面 3s 轮询即 3s 均值） |
| bsp_wifi | 同 ESP-32 工程（重连上限 20 次防死循环；扫描挂起重连） |
| bsp_web | 主实例 16 条路由：`/`、`/api/status|scan|wifi|cam|flash|gpio|sd|sd/save|sd/del|reboot|resetwifi`、`/capture`、`/sd/*`（白名单校验防穿越：仅 `A-Za-z0-9_.`，须含 .jpg，禁 /，长度<16）；流实例 `/stream`。**SOI(FFD8) 校验丢弃损坏帧**（连续 20 帧损坏才断流，快照重试 3 帧） |
| bsp_gpio | 引脚占用表集中定义（1/2/3/4/12/13/14/15/33 + 复用说明）；**SD 挂载期间 2/14/15 拒绝控制**（动态查询 BspSdMounted）；上电不动引脚（全输入态），影子状态记录已配置模式 |
| bsp_sd | **挂载独立任务**；**写卡工作队列任务**；**视频录像（V1.2.0.0）：AVI(MJPEG) 容器分段滚动（REC_年月日-时分秒_段号.avi，未对时 REC_NOSYNC_段号.avi；每段 3000 帧或分辨率变化即换段，收尾回填总帧数/索引可播放）；开机自动续录（NVS recsw/recfps）；满卡循环覆盖（空闲<200MB 自动删最旧 REC_*.avi）；单帧写超 8s 看门狗自停**；抓拍时间戳命名/降级；文件列表/整读/删除/**流式下载（8KB 分块回调，大文件不经内存整缓冲）**；FATFS 全访问经互斥锁串行化 |
| bsp_store | 同 ESP-32 工程，命名空间 cam |

## APP 层功能记录

| 模块 | 关键点 |
|------|--------|
| app_net | 初始化链 bsp_wifi → store → gpio → sd(异步) → cam → **detect** → web；联网后 SNTP 对时（录像/抓拍时间戳命名依赖）；状态 JSON：`ver/mode/ssid/ip/rssi/heap/psram/uptime/size/quality/fps/clients/sensor/sd/sdcap/sdfree`（录像另走 /api/rec，检测另走 /api/detect） |
| app_detect | **人体活动检测+人流量统计（V1.3.0.0，纯算法方案——经典 ESP32 无 NN 算力）**：JPEG 1/8 缩放解码（esp_jpeg 组件 RGB565→80x60 灰度重采样）→ 背景慢更新（τ≈16s）差分 → 洪泛连通域+面积/宽高比人形过滤 → 质心最近邻跟踪（20格半径，2帧确认/3帧丢失）→ 计数线左右状态翻转判进/出（NVS 持久，跨日自动清零）；2fps 分析任务；设置 on/sens/line 网页可调持久化；局限：静止目标≈15s 被背景吸收、与背景同色可能漏检 |
| app_main | 主循环 10ms 槽（当前空槽，业务全事件/请求驱动） |

## 数据通路

| 通路 | 输入 → 输出 |
|------|------------|
| 视频流 | OV3660 → esp32-camera(PSRAM 双缓冲 LATEST) → `BspCamFbGet` → SOI 校验 → 流实例 :81 multipart 推送（单任务单观看路） |
| 快照 | 同上取帧 → 主实例 /capture 一次性应答（与流互不阻塞） |
| SD 抓拍 | 取帧+SOI 校验 → `/sdcard/CAM_xxxx.jpg` → 列表/下载（/sd/* 通配）/删除 |
| 配网 | 浏览器表单 → /api/wifi（同步 12s）→ NVS + STA 连接（失败恢复原配置） |
| NAT 中继 | AP 客户端 → NAPT 改写 → STA 上行（DNS 经 DHCP 下发上游网关） |

## 实测性能与环境（2026-10-10，STA 回传）

- VGA q12：**~22fps**（20KB/帧，3.7Mbps）；UXGA q10：**~2.7fps**（199KB/帧，传感器读出物理上限）——监控建议 VGA/SVGA
- 供电：摄像头+WiFi 峰值电流高，5V ≥2A；弱供会 brownout 反复重启
- 上游网络：PC Windows ICS 热点（YYM_1339，192.168.137.0/24）实测**极不稳**（设备反复被拒/掉线），测试优先直连路由器

## 踩坑记录（按定位顺序）

1. **esp32-camera 2.1.8 @ IDF6.1 API 变更**：`esp_camera_fb_get()` 无参（2.0.x 收超时参数）；`^2.0.3` 依赖解析到 2.1.8
2. **JPEG 帧缓冲按初始档位 宽×高/5 估算**（cam_hal.c `CONFIG_CAMERA_JPEG_MODE_FRAME_SIZE_AUTO`）：运行时切大分辨率 → 帧超出缓冲截断 → `cam_hal: NO-SOI` 花屏卡顿。**治法：`camera_config_t.jpeg_buffer_size` 显式给 UXGA 级 960KB，且初始化即按最大档分配**
3. **httpd `max_uri_handlers` 默认 8**：主实例 10+ 条路由第 9 条起注册失败（本工程踩过 10 条 → 尾巴三条失败），显式设 20
4. **esp_http_server 每实例单任务**：URI 处理器内联执行（httpd_uri.c），死循环流处理器独占实例 → /stream 必须独立实例；/capture 放主实例才不被流阻塞
5. **httpd URI 默认精确匹配**：`/sd/*` 通配路由必须 `Cfg.uri_match_fn = httpd_uri_match_wildcard`，否则 404（httpd 内建 404 是 text/html，与处理器 404 可区分）
6. **通配下载白名单要含小写字母**：`CAM_0001.jpg` 的 `.jpg` 是小写，只放行 A-Z/0-9/_/. 会把合法文件 404
7. **main 组件显式 PRIV_REQUIRES 后失去"默认依赖全部组件"**：esp_wifi/esp_http_server/nvs_flash/esp_timer/heap 等须逐一列出
8. **IDF6.1 `sdmmc_slot_config_t` 在 legacy 头**（esp_driver_sdmmc/legacy/include/driver/sdmmc_host.h，sdmmc_cmd.h 不再带入）；**memset 零值会把 CD/WP 配成 GPIO0（=摄像头 XCLK！）**——必须显式 `SDMMC_SLOT_NO_CD/NO_WP`；未用数据脚用 `GPIO_NUM_NC`
9. **SD 卡疑似劣质三症状**：写入成功但掉电文件丢失 / 目录扫描偶发为空 / 驱动探测挂死（症状：启动后所有模块打印消失=主任务卡死在挂载里，WiFi 日志来自事件任务具迷惑性）。**治法：挂载独立任务化**；换卡并用 PC 读卡器验真（H2testw）
10. **CH340 COM9 烧录 460800 失联**（芯片能连、切波特率后无响应），固定 115200；另一块 CH340 板在 COM3 勿混淆
11. **路由器环境已变**：YYM_4G/YYM_5G → 现 **YYM55**（2.4G ch1）；PC 侧另有 ICS 热点 YYM_1339（192.168.137.0/24，极不稳且 DHCP 会换地址——2026-10-10 从 .199 变 .90，“设备失联”先查新 IP）
12. PSRAM 实测 8MB 只映射 4MB（经典 ESP32 地址空间限制，日志 "map as much as we can" 属正常）
13. **FreeRTOS 任务隔离是治卡顿的正解**：两次实践——SD 挂载后台任务化（驱动挂死不阻塞启动链）、SD 写卡工作队列化（HTTP 提交即应答+超时短路）；劣质卡最坏只拖死单个 sd_* 任务，摄像头/网页/GPIO 全不受影响
14. **开机 CAM 序号扫描禁用 stat 循环**：9999 次 stat 找最大序号在无 CAM_ 文件时要跑 30~60s，把 mounted 日志/自动录像全堵在后面（表象："启动后模块打印消失"）；改目录一次遍历解析 CAM_号（~100ms）
15. **段式写入器的 memset 自伤**：开段函数入口 memset 段结构体，而调用方把段结构体内的 Name/Width/Height 预填后再传入（pName 就是 pAvi->Name 别名）→ 名字被清空 fopen("/sdcard/") 失败、尺寸归零致每段 1 帧无限换段；治法：名字/宽高改参数传入，结构体只存不预填
16. **大文件下载必须流式**：为快照设计的 1MB 整读缓冲会拒掉录像文件（5MB+）→ 下载 404；定长响应头（Content-Length）+ 8KB 分块 socket 推送，内存占用与文件大小无关
17. **esp_jpeg 组件可作检测解码器**：`esp_jpeg_decode` 支持 1/2/1/4/1/8 缩放（RGB565/888），VGA JPEG→80x60 仅约 10-15ms @240MHz；esp32-camera 自带该依赖（conversions），main 显式 PRIV_REQUIRES espressif__esp_jpeg 即可用
18. **检测帧源与流/录像共享 fb 队列**：多消费者 fb_get 各自分到部分帧（2fps 检测+10fps 录像+流媒体 ≈13fps ≤ 传感器能力）；检测解码后自建固定 80x60 网格重采样，任意分辨率统一处理

## 构建与烧录

```powershell
cmd /c "call F:\00.Code\11ESP\idf-env.bat && cd /d F:\00.Code\11ESP\ESP && idf.py build"
cmd /c "call F:\00.Code\11ESP\idf-env.bat && cd /d F:\00.Code\11ESP\ESP && idf.py -p COM9 -b 115200 flash"
```

- `flash` 保留 NVS（配网/摄像头设置不丢）；改 `sdkconfig.defaults` 后须删 `sdkconfig` 重新生成（坑同 ESP-32 工程）
- 验证：串口 115200 看 `app start → ap ready → hal_cam ready → bsp_web ready → app_net ready`；`/api/status` 最省事的端到端探针
