# ESP32-CAM 网页视频监控工程功能记录

- **板卡**:AI-Thinker ESP32-CAM(SoC:ESP32-D0WDQ6,双核 Xtensa LX6 @ 240MHz,4MB Flash / **实测板载 8MB PSRAM**--经典 ESP32 最多映射 4MB)
- **传感器**:**OV3660**(实测 PID=0x3660,标称 OV2640 的板子实际装了 OV3660,驱动自动识别;UXGA 上限,QXGA 不启用)
- **SDK**:ESP-IDF **v6.1**(Windows 激活脚本 `F:\00.Code\11ESP\idf-env.bat`;**Linux YYM 机**:IDF 仓库 `/mnt/sda1/esp-idf`(v6.1 tag,SSH 22 直连克隆)、工具链 `IDF_TOOLS_PATH=/mnt/sda1/espressif`(install.sh 须加 `IDF_GITHUB_ASSETS=dl.espressif.com/github_assets` 走乐鑫镜像,github 直下被拒);构建 `export IDF_TOOLS_PATH=/mnt/sda1/espressif && source /mnt/sda1/esp-idf/export.sh && idf.py build`);摄像头驱动 **esp32-camera 2.1.8**(组件仓库自动拉取,`main/idf_component.yml` 声明)
- **版本号规则**:同 ESP-32 工程(V主.次.大功能.小功能);当前 **V1.4.2.5**(人流量统计开关化默认关;新增外部视觉检测引擎:API优先本地回退,端点网页可配,联动打通;场景联动拆独立页;前版 1.4.2.4 场景联动)
- **代码仓**:`https://gitee.com/YYM642443594/ESP.git` 分支 `feature/ESP32-Camer`(串口透传工程见 develop 分支;Linux YYM 机本地副本 `/home/yym/sda1/ESP`,构建产物 `build/esp32_cam.bin`);架构/分层规范同 ESP-32 工程(APP→BSP→HAL→ESP-IDF,见仓库 `Project_Level_Skill.md`)
- **网页端**:暗色单页四标签(配网/视频监控/GPIO 控制/存储),配网栈与网页谱系移植自 develop 分支(ESP8266-develop 参照)

## 硬件资源占用表

| 外设 | 引脚/资源 | 用途 | 归属模块 |
|------|-----------|------|----------|
| 摄像头 DVP | XCLK=0, SIOD=26, SIOC=27, Y2=5, Y3=18, Y4=19, Y5=21, Y6=36, Y7=39, Y8=34, Y9=35, VSYNC=25, HREF=23, PCLK=22, PWDN=32 | OV3660 并口(固定接线) | hal_cam |
| SD 卡槽 | CLK=14, CMD=15, D0=2(**1-bit 模式**;D1=4 留补光灯/D2=12/D3=13 留 GPIO) | 抓拍存储 FATFS `/sdcard` | bsp_sd |
| 补光灯 | GPIO4(与 SD D1 复用,1-bit 模式下归补光灯) | 板载高亮 LED | hal_cam |
| 板载红色 LED | GPIO33 | GPIO 控制页可控 | hal_gpio/bsp_gpio |
| 剩余可控 GPIO | 1/3(UART0 日志口,控制后串口失联)、2/4/12/13/14/15/33 | 网页 GPIO 控制页 | bsp_gpio |
| 不可用 | GPIO0=摄像头 XCLK;GPIO16/17=PSRAM;GPIO6~11=Flash;GPIO34~39 仅输入且被摄像头占用 | - | - |
| WiFi | SoftAP `ESP32_Config`/192.168.4.1 + STA;NAPT 借道上网 | 配网/监控/NAT 中继 | hal_wifi/bsp_wifi |
| 下载口 | Windows=**COM9**,Linux YYM 机=**/dev/ttyUSB1**(CH340,**必须 115200**--460800 连接后失联;ESP8266 同机占 /dev/ttyUSB0,勿混淆) | 烧录/日志 | - |



## 遗留Bug记录

​	该章节有遗留bug内容均为人工测试发现的bug记录,修改完成后需要填写修复状态和修复时间;

|   版本   | 问题记录                                                     | 测试时间   | 修复状态 | 修复时间 |
| :------: | ------------------------------------------------------------ | ---------- | -------- | -------- |
| V1.4.2.2 | 邮件推送界面的功能不能正常发送邮件                           | 2026.10.16 | 已修复(网络层 V1.4.2.2+交互层+TLS 配置/内存深层三层修复,测试邮件实测送达,见踩坑 28/29/30) | 2026.10.19 |
| V1.4.2.2 | 页面中运行时间的走时是3秒钟跳一次吗,不是一秒跳一次          | 2026.10.16 | 已修复(状态轮询 3s→1s,uptime 本身来自 esp_timer 精确,纯显示轮询问题) | 2026.10.19 |
| V1.4.2.2 | 人体检测经常出现误判,在没有人的时候也会进行框选然后判断为有人进行计数,是否可以考虑接入一些开源的API来判断识别是否有人,或者加入一些开源的算法来判断是否有人 | 2026.10.16 | 已修复(全局光照突变改"超阈像素占比>45%"判据拦截 AEC/灯光类误报;接入 API 方案不采纳:监控需实时性+内网可用+零调用成本,纯算法优化后已够用,见踩坑 28) | 2026.10.19 |
| V1.4.2.2 | 邮件推送界面勾选有人发送邮件的功能,这里的检测不够灵敏,经常出现人在摄像头的跟前也不会触发检测到有人然后发送邮件 | 2026.10.16 | 已修复(两根因:1面积上限 2000 误杀贴近大目标已取消,上限职责改由占比判据承担;2差分膨胀 1 轮连回 JPEG 压缩碎片,周期 350→300ms,见踩坑 28) | 2026.10.19 |
| V1.4.2.3 | 通过邮件发送出去的MP4视频无法正常的播放 | 2026.10.19 | 已修复(非文件损坏:ffprobe验证MP4容器合法全帧可解,根因MJPEG编码浏览器/系统播放器不支持;邮件正文加VLC/PotPlayer播放提示) | 2026.10.20 |
| V1.4.2.3 | 存储界面存储的视频不能正常的查看，且缺少邮件发送功能 | 2026.10.19 | 已修复(新增GET /replay按容器解帧MJPEG流回放,「查看」改内嵌弹层浏览器原生渲染;「邮」按钮POST /api/mail/sendfile复用SMTP管线;另/api/sd加err字段暴露SD异常+启动打复位原因诊断今早两次意外重启) | 2026.10.20 |



## HAL 层功能记录

### hal_cam(摄像头驱动,封装 esp32-camera)

| 功能 | API | 说明 |
|------|-----|------|
| 初始化 | `HalCamInit(pCfg)` | **帧缓冲始终按最大档 UXGA + 显式 `jpeg_buffer_size`=960KB×2 分配**(PSRAM),用户档位(分辨率/质量/镜像/翻转)init 后经传感器接口应用;PSRAM 缺失降级 DRAM+QVGA |
| 取帧/归还 | `HalCamFbGet(ppJpg,pLen,TimeoutMs)` / `HalCamFbReturn(pFb)` | 2.1.x `esp_camera_fb_get()` **无参**(驱动内部固定 4s 超时),帧句柄 void* 透传归还 |
| 参数设置 | `HalCamSizeSet/QualitySet/HmirrorSet/VflipSet` | 运行时可切,流传输中生效于后续帧;档位枚举 QVGA~UXGA 板级映射 |
| 状态查询 | `HalCamSizeGet/QualityGet/HmirrorGet/VflipGet/SensorNameGet/PsramFreeGet` | 传感器状态回读,状态 JSON 用 |
| 补光灯 | `HalCamFlashLedSet/Get` | GPIO4 推挽输出,上电默认灭 |

### hal_wifi(WiFi 驱动,APSTA 双模 + NAPT,develop 移植 + NAT 回迁)

同 ESP-32 工程 hal_wifi(NVS 凭据/扫描/事件回调全套),差异:本工程 V1.1.0.0 回迁了完整 **NAPT 借道上网**(GOT_IP → `ip_napt_enable` + 上游 DNS 写入 AP DHCP + 8s 后踢全部 AP 客户端强制重取含正确 DNS 的租约;断开自动关 NAPT)。`CONFIG_LWIP_IP_FORWARD`+`CONFIG_LWIP_IPV4_NAPT` 必须写 `sdkconfig.defaults`。

### hal_http(HTTP 服务器,双实例 + 流式 API)

| 功能 | API | 说明 |
|------|-----|------|
| 双实例启动 | `HalHttpInit()` | 80 主实例(页面+/api+快照+SD 下载,4 连接,**max_uri_handlers=20**,**uri_match_fn=httpd_uri_match_wildcard**);81 流实例(MJPEG 专用,3 连接,send_wait_timeout=2s,ctrl_port=32769) |
| URI 注册 | `HalHttpUriRegister(pUriCfg)` | `HalHttpUri_S` 含 `StreamIns` 字段路由到流实例 |
| 请求处理 | `HalHttpReqContentLen/Recv/Respond/UriGet` | 通用 GET/POST 应答;UriGet 供通配路由解析路径 |
| 流式响应 | `HalHttpStreamOpen(pReq,pBoundary)` / `HalHttpStreamSend(pReq,pBuf,Len)` | multipart 响应头 + socket 原始 send(连续 3 次 SO_SNDTIMEO 超时全零发才判死,瞬时慢客户端不断流) |

### hal_gpio(通用 GPIO 驱动)

`HalGpioSetup(Num,Mode,Level)`:输入浮空/上拉/下拉/推挽输出;GPIO6~11 Flash 黑名单拒绝,34~39 仅允许输入浮空。`HalGpioRead` 实时电平回读(输入/输出均可读)。

## BSP 层功能记录

| 模块 | 关键点 |
|------|--------|
| bsp_cam | NVS(命名空间 cam)持久化 fsz/jq/hm/vf 四键;帧率统计(两次查询差折算,页面 3s 轮询即 3s 均值) |
| bsp_wifi | 同 ESP-32 工程(瞬时断开无限退避重连 V1.3.0.3;认证类限次 20);**V1.3.0.6 Mesh 防摇摆**:GOT_IP 记忆 BSSID+信道钉住(bssid_set+channel 直连,重连免全信道扫描),连续 8 次直连失败自动解除重扫全网 |
| bsp_web | 主实例 16 条路由:`/`、`/api/status|scan|wifi|cam|flash|gpio|sd|sd/save|sd/del|reboot|resetwifi`、`/capture`、`/sd/*`(白名单校验防穿越:仅 `A-Za-z0-9_.`,须含 .jpg,禁 /,长度<16);流实例 `/stream`。**SOI(FFD8) 校验丢弃损坏帧**(连续 20 帧损坏才断流,快照重试 3 帧) |
| bsp_gpio | 引脚占用表集中定义(1/2/3/4/12/13/14/15/33 + 复用说明);**SD 挂载期间 2/14/15 拒绝控制**(动态查询 BspSdMounted);上电不动引脚(全输入态),影子状态记录已配置模式 |
| bsp_sd | **挂载独立任务**;**写卡工作队列任务**;**视频录像(V1.2.0.0):AVI(MJPEG) 容器分段滚动(REC_年月日-时分秒_段号.avi,未对时 REC_NOSYNC_段号.avi;每段 3000 帧或分辨率变化即换段,收尾回填总帧数/索引可播放);开机自动续录(NVS recsw/recfps);满卡循环覆盖(空闲<200MB 自动删最旧 REC_*.avi;每段收尾与开段失败路径都触发清理,段序号开机扫目录续接防同名覆盖);单帧写超 8s 看门狗自停**;抓拍时间戳命名/降级;文件列表/整读/删除/**流式下载(8KB 分块回调,大文件不经内存整缓冲)**;FATFS 全访问经互斥锁串行化 |
| bsp_store | 同 ESP-32 工程,命名空间 cam |

## APP 层功能记录

| 模块 | 关键点 |
|------|--------|
| app_net | 初始化链 bsp_wifi → store → gpio → sd(异步) → cam → **detect** → web;联网后 SNTP 对时(录像/抓拍时间戳命名依赖);状态 JSON:`ver/mode/ssid/ip/rssi/heap/psram/uptime/size/quality/fps/clients/sensor/sd/sdcap/sdfree`(录像另走 /api/rec,检测另走 /api/detect) |
| app_vision | **外部视觉检测(V1.4.2.5 新增,API优先+本地回退)**:HTTP 端点 POST base64<JPEG>→{boxes:[[x,y,w,h,conf,cls]千分比]};三态模式(0仅本地/1仅API/2API优先);连续3次失败自动回退本地算法,恢复切回;URL/间隔网页可配NVS持久;SPIRAM 48KB base64缓冲;检出目标走本地同套联动(0→1录像+邮件);实测假端点回退/真端点在线/断电保存全通过;适合 CodeProject.AI/YOLO网关/百度云经网关转换 |
| app_detect | **人体活动检测+人流量统计(V1.3.0.0 起,纯算法方案--经典 ESP32 无 NN 算力)**:JPEG 1/8 缩放解码(esp_jpeg 组件 RGB565→80x60 灰度重采样)→ 背景慢更新(τ≈16s)差分 → **全局光照突变占比判据(>45% 丢帧,V1.4.2.3)** → **差分膨胀 1 轮(V1.4.2.3)** → 洪泛连通域+面积/宽高比人形过滤(无面积上限) → 质心最近邻跟踪(20格半径,2帧确认/3帧丢失)→ 计数线左右状态翻转判进/出(NVS 持久,跨日自动清零);约 3fps 分析任务(300ms 周期,V1.4.2.3);设置 on/sens/line 网页可调持久化;局限:静止目标≈15s 被背景吸收、与背景同色可能漏检 |
| app_scene | **场景联动(V1.4.2.4 新增)**:GPIO 输入沿触发→联动输出/拍照邮件/事件录像;4 条规则 NVS 掉电保存;10ms 轮询+50ms 去抖(连续5采样)+10s 冷却;沿类型升/降/双;动作掩码可组合;输出 HoldSecs 自动回退(0=保持);网页 GPIO 页规则配置(增改/触发计数/测试按钮);strapping 脚(GPIO0/12)硬拒+SD 总线脚校验;引脚配置 5s 周期自愈(SD 后台挂载重置 IO_MUX);实测:上升沿触发→GPIO4 置高 10s 精确回退✅;**坑:场景 API 响应 Content-Length 必须 strlen 按 UTF-8 字节数(中文硬编码长度截断);输出脚自愈重配会清联动电平→自愈只配输入脚** |
| app_mail | **邮件推送(V1.4.1.x 新增)**:检测触发/网页测试 → 队列→发送任务;SMTP 隐式 SSL(esp-tls,不挂证书 bundle:QQ/163 下发链缺中间证书);触发瞬间先拍照缓存 SPIRAM(照片与检测时刻对齐,V1.4.1.5);事件录像开启时等段收尾后随邮件附视频(base64 流式分块);60s 节流;配置 NVS 持久;**V1.4.2.2 网络层修复:短写循环续传(TLS SO_SNDTIMEO 到期返短计数)/30s 总预算/TLS 连接失败自动重试 2 次/GOT_IP 后关 STA 省电(DTIM 休眠致下行丢段)/分层错误码(esp 0x8000 系+mbedtls+sock errno,网页映射具体原因)**;**V1.4.2.3 交互修复:测试按钮先自动 POST 当前表单再 test=1(测旧配置坑)** |
| app_main | 主循环 10ms 槽(当前空槽,业务全事件/请求驱动) |

## 数据通路

| 通路 | 输入 → 输出 |
|------|------------|
| 视频流 | OV3660 → esp32-camera(PSRAM 双缓冲 LATEST) → `BspCamFbGet` → SOI 校验 → 流实例 :81 multipart 推送(单任务单观看路) |
| 快照 | 同上取帧 → 主实例 /capture 一次性应答(与流互不阻塞) |
| SD 抓拍 | 取帧+SOI 校验 → `/sdcard/CAM_xxxx.jpg` → 列表/下载(/sd/* 通配)/删除 |
| 配网 | 浏览器表单 → /api/wifi(同步 12s)→ NVS + STA 连接(失败恢复原配置) |
| NAT 中继 | AP 客户端 → NAPT 改写 → STA 上行(DNS 经 DHCP 下发上游网关) |

## 实测性能与环境(2026-10-10,STA 回传)

- VGA q12:**~22fps**(20KB/帧,3.7Mbps);UXGA q10:**~2.7fps**(199KB/帧,传感器读出物理上限)--监控建议 VGA/SVGA
- 供电:摄像头+WiFi 峰值电流高,5V ≥2A;弱供会 brownout 反复重启
- 上游网络:PC Windows ICS 热点(YYM_1339,192.168.137.0/24)实测**极不稳**(设备反复被拒/掉线),测试优先直连路由器

## 踩坑记录(按定位顺序)

1. **esp32-camera 2.1.8 @ IDF6.1 API 变更**:`esp_camera_fb_get()` 无参(2.0.x 收超时参数);`^2.0.3` 依赖解析到 2.1.8
2. **JPEG 帧缓冲按初始档位 宽×高/5 估算**(cam_hal.c `CONFIG_CAMERA_JPEG_MODE_FRAME_SIZE_AUTO`):运行时切大分辨率 → 帧超出缓冲截断 → `cam_hal: NO-SOI` 花屏卡顿。**治法:`camera_config_t.jpeg_buffer_size` 显式给 UXGA 级 960KB,且初始化即按最大档分配**
3. **httpd `max_uri_handlers` 默认 8**:主实例 10+ 条路由第 9 条起注册失败(本工程踩过 10 条 → 尾巴三条失败),显式设 20
4. **esp_http_server 每实例单任务**:URI 处理器内联执行(httpd_uri.c),死循环流处理器独占实例 → /stream 必须独立实例;/capture 放主实例才不被流阻塞
5. **httpd URI 默认精确匹配**:`/sd/*` 通配路由必须 `Cfg.uri_match_fn = httpd_uri_match_wildcard`,否则 404(httpd 内建 404 是 text/html,与处理器 404 可区分)
6. **通配下载白名单要含小写字母**:`CAM_0001.jpg` 的 `.jpg` 是小写,只放行 A-Z/0-9/_/. 会把合法文件 404
7. **main 组件显式 PRIV_REQUIRES 后失去"默认依赖全部组件"**:esp_wifi/esp_http_server/nvs_flash/esp_timer/heap 等须逐一列出
8. **IDF6.1 `sdmmc_slot_config_t` 在 legacy 头**(esp_driver_sdmmc/legacy/include/driver/sdmmc_host.h,sdmmc_cmd.h 不再带入);**memset 零值会把 CD/WP 配成 GPIO0(=摄像头 XCLK!)**--必须显式 `SDMMC_SLOT_NO_CD/NO_WP`;未用数据脚用 `GPIO_NUM_NC`
9. **SD 卡疑似劣质三症状**:写入成功但掉电文件丢失 / 目录扫描偶发为空 / 驱动探测挂死(症状:启动后所有模块打印消失=主任务卡死在挂载里,WiFi 日志来自事件任务具迷惑性)。**治法:挂载独立任务化**;换卡并用 PC 读卡器验真(H2testw)
10. **CH340 COM9 烧录 460800 失联**(芯片能连、切波特率后无响应),固定 115200;另一块 CH340 板在 COM3 勿混淆
11. **路由器环境已变**:YYM_4G/YYM_5G → 现 **YYM55**(2.4G ch1);PC 侧另有 ICS 热点 YYM_1339(192.168.137.0/24,极不稳且 DHCP 会换地址--2026-10-10 从 .199 变 .90,"设备失联"先查新 IP)
12. PSRAM 实测 8MB 只映射 4MB(经典 ESP32 地址空间限制,日志 "map as much as we can" 属正常)
13. **FreeRTOS 任务隔离是治卡顿的正解**:两次实践--SD 挂载后台任务化(驱动挂死不阻塞启动链)、SD 写卡工作队列化(HTTP 提交即应答+超时短路);劣质卡最坏只拖死单个 sd_* 任务,摄像头/网页/GPIO 全不受影响
14. **开机 CAM 序号扫描禁用 stat 循环**:9999 次 stat 找最大序号在无 CAM_ 文件时要跑 30~60s,把 mounted 日志/自动录像全堵在后面(表象:"启动后模块打印消失");改目录一次遍历解析 CAM_号(~100ms)
15. **段式写入器的 memset 自伤**:开段函数入口 memset 段结构体,而调用方把段结构体内的 Name/Width/Height 预填后再传入(pName 就是 pAvi->Name 别名)→ 名字被清空 fopen("/sdcard/") 失败、尺寸归零致每段 1 帧无限换段;治法:名字/宽高改参数传入,结构体只存不预填
16. **大文件下载必须流式**:为快照设计的 1MB 整读缓冲会拒掉录像文件(5MB+)→ 下载 404;定长响应头(Content-Length)+ 8KB 分块 socket 推送,内存占用与文件大小无关
17. **esp_jpeg 组件可作检测解码器**:`esp_jpeg_decode` 支持 1/2/1/4/1/8 缩放(RGB565/888),VGA JPEG→80x60 仅约 10-15ms @240MHz;esp32-camera 自带该依赖(conversions),main 显式 PRIV_REQUIRES espressif__esp_jpeg 即可用
18. **检测帧源与流/录像共享 fb 队列**:多消费者 fb_get 各自分到部分帧(2fps 检测+10fps 录像+流媒体 ≈13fps ≤ 传感器能力);检测解码后自建固定 80x60 网格重采样,任意分辨率统一处理
19. **断网重连策略(V1.3.0.3)**:断开必须按原因分类--认证类(密码错:reason 15/202/204)限次防死循环;瞬时类(NO_AP_FOUND/BEACON_TIMEOUT 等,如路由器重启、热点还没开)**无限退避重连**(前 3 次立即,后 5s→30s 循环)。旧版 20 次总限会在 PC 重启期间 ICS 热点关闭几分钟的场景下永久掉线(实测:设备开机永远连不上)
20. **PC 重启会换 COM 口**:USB 重新枚举导致 CH340 从 COM9 变 COM4(2026-10-12 实测);烧录前先 `Get-CimInstance Win32_PnPEntity | ? Name -match CH340` 枚举当前口;Windows ICS 热点(YYM_1339)重启后可能自动关闭且极不稳,长期部署应改连主路由
21. **Linux YYM 机首次构建环境(2026-10-15)**:IDF 克隆须走 `git@github.com:22` 直连(HTTPS 被墙、`ssh.github.com:443` 被热点 captive DNS 劫持到 192.168.4.1);ssh config 里 `Host github.com → ssh.github.com:443` 会让 `--recursive` 子模块克隆 rc=128,绕法 `GIT_SSH_COMMAND='ssh -F /dev/null -i ~/.ssh/id_ed25519_esp8266'`;工具链 install.sh 必加 `IDF_GITHUB_ASSETS=dl.espressif.com/github_assets` 镜像;export 前必须 `export IDF_TOOLS_PATH=/mnt/sda1/espressif`(否则默认找 ~/.espressif 报 python_env 不存在);烧录 `idf.py -p /dev/ttyUSB1 -b 115200 flash`
22. **ESP32 板插入 Linux 不出串口=USB 枚举失败(error -71)**:dmesg 表现 `device descriptor read/64, error -71` 反复重试后 `unable to enumerate`(线材/接触/供电问题,与 CH340 驱动无关);换插拔/换口后恢复;同机 ESP8266 的 serial_sim.py 会因同类 USB 抖动写失败 -71 退出,烧录前后记得 `ps | grep serial_sim` 补拉起
23. **idf.py monitor 非 TTY 也能用**:stdin 非 TTY 时自动进非交互模式(支持 expect/sleep 子命令),重定向日志后 grep 关键启动行(`hal_cam ready/bsp_web ready/app_net ready`)即可无头验证;首帧 NO-SOI 是 OV3660 上电初始化现象,第三帧起正常,固件 SOI 校验兜底
24. **页面"加载后卡死/按钮全无反应"=JS 语法错误被浏览器静默丢弃(V1.3.0.4)**:detRender 检测线同步 if 块少一个闭合 `}`,整个 `<script>` 解析失败,所有 onclick 不绑定(页面骨架/文字照常显示,纯 curl 和 /api/status 探测发现不了);排查法:把下发 HTML 的 script 段抽出来 `node --check`;预防法:页面改动后构建前先做该校验
25. **SD 统计对不上账 + 满卡死锁(V1.3.0.5,四处)**:1`/api/sd` 文件列表硬截 40 条而驱动存 128 条→"可见文件合计 102MB vs 已用 7.5GB"对不上账,修=列表上限对齐驱动+JSON 缓冲 4096→8192;2满卡清理只挂在"手动停止录像"分支,自动续录/写满自停/开段失败路径全不清理→卡满永久滞留,修=每段收尾+开段失败都清理;3清理删除上限 Guard<200,卡上碎片文件超 200 个时删不到 KEEP_FREE 就放弃,修=1024(反正"无可删/删失败"会提前退出);4录像段序号 G_RecSeq 开机重置为 1+`fopen wb`=未对时 NOSYNC 命名开机同名静默覆盖旧录像(抓拍 G_SnapSeq 有续号而录像没有,移植时漏了),修=挂载后目录一次遍历取 REC_*_NNNN 最大段号+1。教训:**统计类功能必须拿"驱动真实计数"对账(串口 `list refresh: N files` 日志)**,API 返回的列表数≠卡上真实文件数

26. **Mesh/多 AP 同名环境 SoftAP "消失"(V1.3.0.6)**:环境里同名 SSID 有 3 个 BSSID(信道 1/6/11),ESP32 STA 按信号选节点,位置差时摇摆关联到 -80dBm 弱节点→beacon 丢失(`state: run -> init (0x2c0/0x9c0)`)循环断连;**每次断连重连都要全信道扫描 2~3s,单射频 APSTA 下扫描期间 SoftAP 停发信标且 AP 信道跟随 STA 跳变(日志 `ap channel adjust o:6,1 n:11,2`)→外部看 AP 忽隐忽现/彻底搜不到,已连客户端被踢**--表象是"WiFi 搜不到",实际 STA 在疯狂重连。治法:GOT_IP 时记忆节点 BSSID+信道,断线重连 `bssid_set=true`+`channel` 单信道直连(无扫描,SoftAP 几乎不断);连续 8 次直连失败自动解除钉住恢复全信道扫(适应节点下线/挪位,连上后重新钉)。诊断抓手:`nmcli -f SSID,BSSID,CHAN,SIGNAL dev wifi list` 看同名多 BSSID;串口 grep `connected with` 对比历次 bssid

27. **JPEG 残影排查与 EOI 校验加固(V1.3.0.7)**:用户实测"物体快速移动时画面偶发小残影"。排查:软件链路无截断/错位可能(fb 960KB 远大于 VGA 帧;HalHttpStreamSend 循环补发保 Content-Length 对位),残影主体是**物理特性**--OV3660 逐行曝光(一帧上下行曝光时刻不同→快移物体形变)+ 室内曝光时间 20~40ms(运动模糊)+ VGA q12 高压缩块效应(运动边缘高频细节被丢成细碎"蚊子噪声"块,运动一停下帧即干净);**防御性加固**:原 BspWebJpegOk/BspSdJpegOk 仅查 SOI 头(FFD8),半截截断帧静默过检--流端浏览器解码半截 JPEG 会**保留上一帧局部内容**(真"残影"式软件成因)、录像端坏帧进 AVI 花屏;补查 EOI 尾(FFD9)后流/抓拍/录像全部入口拦截首尾损坏帧。教训:**"看起来像软件问题的现象先量化物理成因再动代码",帧完整性校验头尾都要查(单查 SOI 拦不住尾部截断)**

28. **四项实测 bug 的根因与修法(V1.4.2.3,2026-10-19)**:
    - **"人在跟前反而不触发"(漏报两根因)**:1旧面积上限 `DET_MAX_AREA=2000` 本意拦截"全局变化",但人贴近镜头占屏 40%+ ≈2000+ 格直接被误杀--目标大小与光照突变是两个维度,不能拿面积上限当全局判据;2JPEG 高压缩下大目标差分图碎裂成多个小块,各自小于面积门槛被滤(膨胀 1 轮十字连通后修复,单像素噪声膨胀后仅 5 格十字仍小于门槛不引误报)。检测周期 350→300ms。**教训:面积上限这种"全屏级 Guard"要拿真实目标尺寸分布校准,贴脸目标恰恰是最大的合法目标**
    - **无人时误判有人(误报)**:AEC 步进/开关灯时全帧均匀超阈产生大域伪目标。修法:全局光照突变改"超阈像素占比>45% 丢帧"判据(光照突变占比常 >80%,局部人目标 <40%,分界清晰);丢帧时背景照常快更新,下一帧起新光照立即生效。**关于接入开源 API/NN:不采纳--监控要 24h 实时(API 延迟+配额+断网失效),经典 ESP32 无 NN 算力(ESP-DL 人形模型仅 S3),占比判据+膨胀+跟踪确认已把误报压住**
    - **运行时间 3 秒跳一次**:uptime 来自 `esp_timer_get_time()/1e6` 本身精确,纯网页轮询 setInterval(refresh,3000) 所致,改 1s。注意 fps 显示是两次 /api/status 查询差折算,1s 窗口仍有效(>0.5s 下限)但数值轻微跳动
    - **邮件不能正常发送(两层叠加)**:网络层 V1.4.2.2 已修(短写续传/30s 预算/自动重试/关 STA 省电);交互层 V1.4.2.3 补修--测试按钮直接 `test=1` 不落表单,填完不点保存就测试=测设备里旧配置必败,现测试前自动把当前表单 POST 一遍。**教训:配置页有"保存"和"测试"两个动作时,测试必须先隐式保存(或禁用测试直到已保存),用户不会按你想的顺序操作**
29. **Linux YYM 机 IDF 环境二次踩坑(2026-10-19)**:1系统 python3 从 3.10 升到 3.12 后 venv 软链 `python_env/idf6.1_py3.10_env/bin/python3` 跟着指向 3.12,export 报 rich 缺失/环境不存在--修法:重建软链指向 `/usr/bin/python3.10`,且 export 前加 `IDF_PYTHON_ENV_PATH` 显式指定;2build 目录残留半配置状态会在 `toolchain/cflags` 尾部残留自引用 `@cflags` 行,gcc 报 `too many @-files encountered`(响应文件递归)--修法:`rm -rf build` 全新配置;3cmake 用 /usr/bin 的 3.28(IDF 要求 4.0.3 但兼容),ninja 未装走 Unix Makefiles;4烧录口权限:yym 不在 dialout 组且无 sudo 免密,`chmod 666 /dev/ttyUSB1` 需提权(长期解法 `sudo usermod -aG dialout yym` 后重新登录);5**idf.py set-target/fullclean 重生成 sdkconfig 会丢弃手工改动**--ESP_TLS_INSECURE/SKIP_SERVER_CERT_VERIFY 曾只改在 sdkconfig(c6c4deb),fullclean 后静默回归,邮件 TLS 直接 0x8017(No server verification option set),**所有 sdkconfig 手工改动必须同步写进 sdkconfig.defaults**
30. **邮件 TLS 深层根因(2026-10-19 终版)**:0x8017 有两层:1上面坑29-5 的证书跳过配置丢失;2**MBEDTLS_INTERNAL_MEM_ALLOC=y(默认)强制 SSL 走内部 RAM**--检测+事件录像+流媒体并发时内部 RAM 挤干,mbedtls_ssl_setup 的 in_buf(16KB,MBEDTLS_SSL_IN_CONTENT_LEN)+out_buf(4KB)calloc 失败返回 tls=141(=PSA_ERROR_INSUFFICIENT_MEMORY,MBEDTLS_ERR_SSL_ALLOC_FAILED 在 PSA 化后不再是负十六进制而是 PSA 码)-->esp 层 0x8017。修=CONFIG_MBEDTLS_EXTERNAL_MEM_ALLOC=y(SSL 缓冲走 8MB PSRAM,邮件低频后台任务性能无感)+app_mail 任务栈 8192→12288。诊断抓手:/api/mail 的 err/whex/sock 三元组+串口 grep "ssl_setup returned";**教训:自由堆大的系统也要盯内部 RAM 专用的分配链,PSA 化后 ALLOC_FAILED 错误码形态变了(141 而非 -0x7F00 系)**

## 版本历史

| 版本 | 日期 | 提交 | 说明 |
|------|------|------|------|
| V1.4.2.3 | 10-19 | 70c3b8e | 【修复】四项实测 bug：①邮件测试前自动落当前表单（测旧配置必败的交互坑）②状态轮询 3s→1s（运行时间每秒跳）③检测误报：全局光照突变改超阈占比>45%判据，取消面积上限 2000（误杀贴脸大目标）④差分膨胀 1 轮连回 JPEG 压缩碎片（大/远目标碎裂漏检），周期 350→300ms |
| V1.3.0.7 | 10-16 | f916f52 | 【加固】JPEG 帧完整性校验补 EOI 尾标记(FFD9)——原仅查 SOI，截断帧静默过检（流端浏览器解码半截 JPEG 保留上一帧局部内容=残影式缺陷，录像端坏帧花屏）；流/抓拍/录像全入口生效。快移残影主体为物理特性（逐行曝光+运动模糊+高压缩块效应），详见踩坑 27 |
| V1.3.0.6 | 10-15 | 585c251 | 【修复】Mesh 多 AP 环境 AP "消失":STA 钉住 BSSID+信道免扫描重连;8 次失败自动解锁重扫。含 SD 劣质卡 write stall 观测记录(8s 看门狗自停正常兜底) |
| V1.3.0.5 | 10-15 | 5ad2ca6 | 【修复】SD 统计/回收四处:网页列表 40→128 条(缓冲 8192);满卡清理每段收尾+开段失败都执行;清理上限 200→1024;段序号开机续接防 NOSYNC 同名覆盖。实测 free 124→266MB 自动回收 |
| V1.3.0.4 | 10-15 | 9ebe5c0 | 【修复】配网页所有按钮无反应:detRender 少闭合大括号致整个 script 被浏览器丢弃(V1.3.0.x 检测 UI 引入的 JS 回归) |
| V1.3.0.3 | 10-15 | dfe2dae | 【修复】开机连不上网:瞬时断开改无限退避重连(前 3 次立即,后 5s→30s 循环自愈),认证类限次 |
| V1.3.0.0 | 10-12 | - | 【新增】人体活动检测+人流量统计(纯算法:差分+连通域+质心跟踪+计数线) |
| V1.2.0.0 | 10-11 | - | 【新增】SD 视频录像 AVI(MJPEG) 分段滚动+满卡循环覆盖+开机自动续录 |
| V1.1.0.0 | 10-10 | - | 【增强】NAPT 借道上网回迁(AP 客户端经 STA 上行) |
| V1.0.x | 10-08~ | - | 初版:配网/视频流/抓拍/GPIO 控制/SD 管理 |

## 构建与烧录

```powershell
cmd /c "call F:\00.Code\11ESP\idf-env.bat && cd /d F:\00.Code\11ESP\ESP && idf.py build"
cmd /c "call F:\00.Code\11ESP\idf-env.bat && cd /d F:\00.Code\11ESP\ESP && idf.py -p COM9 -b 115200 flash"
```

- **Linux YYM 机**:`export IDF_TOOLS_PATH=/mnt/sda1/espressif && source /mnt/sda1/esp-idf/export.sh && cd /home/yym/sda1/ESP && idf.py build`;烧录 `idf.py -p /dev/ttyUSB1 -b 115200 flash`
- `flash` 保留 NVS(配网/摄像头设置不丢);改 `sdkconfig.defaults` 后须删 `sdkconfig` 重新生成(坑同 ESP-32 工程)
- 验证:串口 115200 看 `app start → ap ready → hal_cam ready → bsp_web ready → app_net ready`;`/api/status` 最省事的端到端探针
