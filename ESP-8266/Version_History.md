# ESP8266-XCOM 版本修改史

> 依据代码仓库 git log 逐条整理（2026-09-30）；早期提交无正式版本号（stage 阶段号/无号），自 V1.0.2.x 起版本号写入 `APP_WEB_VER`（app_web.cpp），规则：小修第四位 +1，大改第三位 +1 且第四位保留。

## V1.0.2.x 系列（正式版本号）

| 版本 | 日期 | 提交 | 内容 |
|------|------|------|------|
| V1.0.5.6 | 10-13 | （本次提交） | 【修复】门户大页低 heap 随机截断（手机经热点 NAT 回访 STA IP 时页面只剩骨架：无版本号、标签切不动；PC 走 AP 直连 10 连拉 3 次截断）——41KB 明文单次 send 让 LWIP 一次性铺发送缓冲，heap≈10KB 时 pbuf 分配失败半路放弃。三层修复：①门户页 gzip 预构建（scripts/build_web_gz.py 挂 extra_scripts=pre，明文 app_web_page.h 仍是唯一编辑源，生成 app_web_page_gz.h 内嵌 13085B 压缩体=1/3.1，Flash 53.0%→50.3%，脚本内 gzip round-trip 逐字节校验；网页仅需 Content-Encoding: gzip 头，浏览器全兼容页面 JS 零改动）②DrvWebSendRawBin 二进制发送通道（drv/bsp 三层透传）③1KB 分块 write_P 直写 socket+短写重试+4s 超时放弃（sendContent_P 库内忽略 write 返回值短写静默丢尾，实测 19/20 仍截一次；改直写后 25/25 全完整）；服务端实测：AP 侧 25 连拉零截断，Content-Encoding: gzip+no-store 在位；verify.sh 门户页判定升级为"gzip 解压与本地源码逐字节比对"；RAM 60.9%/Flash 50.3% |
| V1.0.5.12 | 10-13 | 5724f61 | 【修复】网页串口终端周期性卡顿数秒（压力流下每 2~3 秒一次）——三层同步写阻塞叠加：① WebSockets 库 broadcastBIN 对慢客户端（手机息屏/弱链路 TCP 零窗口）的写死循环超时默认 5s（WEBSOCKETS_TCP_TIMEOUT 编译期压到 100ms，终端流式数据慢客户端丢帧下帧即追）② 转发 TCP/MQTT 裸写 EMQX TLS 连接无上限（新增 DrvNetClientCanWrite 查 LWIP availableForWrite 水位，不足丢本批防阻塞，与 HTTP 分支不排队哲学一致）③ 云写包 500ms 上限；配套诊断基建：主循环分段耗时（MLP_SEG 五段：web/uart/fwd/cloud/wifi，/api/status 暴露 lp/lpmax/lpn）+ 慢圈黑匣子（G_SlowRing[16] 记录 >800ms 圈的 uptime/分段/耗时/云 Tag/Heap，/api/status 暴露 slow 数组）。实测：压力流 50s 下 seg=1（终端/转发段）零上榜，残留卡顿仅 OneNET TLS 建链期（tag=2，1.1~3.6s/次，平台踢线重连已知问题，退避越拉越长）。RAM 61.0%/Flash 50.6% |
| V1.0.5.14 | 10-13 | 1cb2c9d | 【优化】网页串口终端数据流期间用户无感化——消除剩余卡顿与缺字：① 云建链串口静默门控（AppCloudTryConnect 查串口静默<2s 则顺延 1s 复查，连续让路 10min 强制补链防永不间歇流饿死云重连；OneNET 同步 TLS 建链冻结主循环 1~3.6s 是终端可见卡顿跳变+UART 突发丢字节的最后来源）② 转发外部目标重连同款让路（AppFwdTargetLanIp()=假 且 静默<2s 跳过，新增 AppCloudSerialSilentMs 导出）③ UART RX 缓冲 256B→1KB（Serial.setRxBufferSize，+768B RAM 抗偶发百毫秒级阻塞的突发）④ 新增复位原因遥测 BspSysResetReason（/api/status 的 rst 字段，排查运行中异常重启）。实测：压力流 60s 对账丢包 0.34%（此前压力档 57.65%），黑匣子仅剩让路满 10min 后的强制补链单条，稳态零新增；RAM 61.2%/Flash 50.5% |
| V1.0.5.15 | 10-13 | （本次提交） | 【修复】持续数据流下云/转发重连被静默门控无限搁置（用户实测反馈"转发与物联网平台不自动连接"）：转发 TCP 分支此前只让路无上限、MQTT 分支漏打门控补丁，现两分支统一补 60s 强制补链上限；云让路上限 10min→60s（原值用户侧表现为"一直没连"）。实测：压力流下云每 66~78s 强制补链一次（1.3~1.7s），EMQX 正常自动回连。经验：门控类补丁必须同时回答"永不满足放行条件时怎么办"，且让路上限要按用户可感知时长设置 |
| V1.0.5.3 | 10-12 | 5289989 | 【修复】WiFi 断联后永不自动重连须手动复位：门户暂停门控被永久占死——(a) WS 服务端未开心跳，终端页非正常关闭（掉电/睡眠/刷新丢 Close 帧）后 connectedClients 永不归零；(b) AP 挂站点+持续 HTTP 轮询使 2min 门户窗口无限续期，DrvWifiStaMaintain 的“门户使用中暂停重连”条件永久为真。修复=WS 服务端 enableHeartbeat(15s ping/3s pong 超时×2) 约 35s 剔除僵尸连接（正常浏览器自动 pong 不受影响）+ 暂停封顶 5min 强制试连一次 + /api/status 新增 wfail（重连连续失败计数）便于观察；实测：手搓不回 pong 僵尸客户端 30s 内被踢、活连接挺过 6 轮心跳不误踢、期间 HTTP 0.02~0.14s 秒回；RAM 60.8%/Flash 53.0% |
| V1.0.5.2 | 10-10 | （本次提交） | 【工具】新增 verify.sh 上板自动验证脚本：9 组 13 项回归一键化（基线/串口流/WS/门户页/API/GPIO 写读复原/阻塞检测/云转发快照），自动连断 AP、防御半截响应、不碰破坏性接口 |
| V1.0.5.2 | 10-10 | （本次提交） | 【修复】GPIO 页状态栏"设备时间"错位：全角空格前缀在 grid 容器里成为匿名网格项独占第一列致标签/值错行；去掉前缀恢复成对两列，未同步态保留标签对齐 |
| V1.0.5.1 | 10-10 | （本次提交） | 【修复】云平台凭据缺失时建链门控：空凭据+有互联网时每个退避周期拿空域名 connect，DNS/TCP 同步阻塞主循环数秒——网页串口终端 1~2s 周期性卡顿；新增 `AppCloudCredOk()`（巴法查 uid，阿里/OneNET/腾讯/华为查三元组），缺失挂起建链零开销，填好凭据点应用即恢复；与 V1.0.2.7 NTP 门控互补，DNS 卡主循环两条路径全封死 |
| V1.0.5.0 | 10-10 | （本次提交） | 【新增】华为云 IoTDA 平台接入（proto=5，工程目标 3 补齐第 5 家=**五家云平台全通**）：密钥认证 MQTT 1883 明文（`{product_id}.iot-mqtts.cn-north-4.myhuaweicloud.com`，8883=MQTTS 需 CA），username=device_id，clientId=`{device_id}_0_0_{UTC YYYYMMDDHH}`（官方四段式：身份类型 0=设备ID、签名类型 0=HMACSHA256 不校验时间戳），password=hex(hmac_sha256(UTC时间戳, secret))——**密钥=时间戳/内容=secret**（官方 SDK EncryptWithHMac 源码+官方文档测试向量双核实，方向易反），BearSSL br_sha256_vtable 新增 HMAC-SHA256 纯算法；timestamp 仿官方 SDK gmtime 取 UTC（无 RTC=1970010100 可用，NTP 后自动真实）；上行默认 `$oc/devices/{id}/sys/messages/up`（平台不校验消息格式=裸流透传保真），下行 sys/messages/down 靠平台 CONNACK 后自动订阅 QoS0 系统主题（免 SUBSCRIBE）；云配置槽位 5→6（cloudhw_ 前缀键），proto 上限 5；网页物联网平台标签新增华为云单选+字段标签/占位符/secret 必填校验；版本 V1.0.5.0（第三位+1：新功能大改） |
| V1.0.4.0 | 10-01 | 49110f5 | 【新增】腾讯云 IoT 平台接入（proto=4，工程目标 3 补齐第 4 家）：密钥认证 MQTT 1883 明文（`{pid}.iotcloud.tencentdevices.com`，8883 仅证书认证用），username=`{pid}{dn};12010126;xcom1;4102444800`（sdkappid 官方固定值，expiry 固定 2100 免 RTC），password=hex(hmac_sha1(b64dec(PSK), username));hmacsha1，BearSSL br_sha1_vtable 新增 HMAC-SHA1 纯算法；默认主题 `{pid}/{dn}/data` 订阅+发布（官方默认权限双向通吃，无需控制台建主题）；clientId=`{pid}{dn}`；云配置槽位 4→5（cloudtx_ 前缀键），proto 上限 4；网页物联网平台标签新增腾讯云单选+字段标签/占位符/必填校验（PSK 必填）；签名算法经官方 qcloud_iot_mqtt_sign C 工具对拍一致；版本 V1.0.4.0（第三位+1：新功能大改） |
| V1.0.3.0 | 09-30 | c11355b | 【新增】HTTP 协议转发（proto=4，工程目标 1 补齐）：串口数据攒批 POST + 响应体写回串口（下行）+ 空闲 1s GET 探询；手工报文短连接非阻塞状态机；fhttp_ 槽位键；端到端实测通过 |
| V1.0.2.13 | 09-30 | 9eafc35 | 【优化】GPIO 页设备时钟本地走秒：轮询响应校准基准 + 前端 250ms 渲染，消除 2s 轮询造成的约 1s 显示滞后；切离页面停表 |
| V1.0.2.12 | 09-30 | 386067c | 【新增】芯片绑定校验+沉默降级防克隆：app_bind 模块，HMAC-MD5(芯片ID) 绑定（bindid/bindfl 键），3 次宽容后禁 AP/门户/终端/转发/云 |
| V1.0.2.11 | 09-29 | 6f9e573 | 【优化】配网页重启/清除配网按钮完整反馈闭环：轮询 /api/status 检测 uptime 归零判定重启完成，显示等待秒数，完成后自动刷新 |
| V1.0.2.10 | 09-29 | 3afc019 | 【新增】转发配置按协议分槽存储（ftcp_/fudp_/fmqtt_ 前缀键，sel=1 切换语义，旧键一次性迁移）；【修复】局域网 IP 字面量目标豁免 NTP 门控；【优化】网页终端 DocumentFragment+rAF 批量渲染 |
| (V1.0.2.8/.9) | — | （并入 .10 提交） | 转发切换/保存语义冲突修复（sel=1 标记）与分槽迁移修复的开发过程版本 |
| V1.0.2.7 | 09-29 | bc3941e | 【修复】无互联网时阻塞式 connect 卡主循环致终端卡顿：NTP 未同步跳过建链，退避 4s→16s→64s→256s 封顶 300s |
| V1.0.2.6 | 09-29 | d5be215 | 【修复】重启后云平台拿空凭据连不上：AppConfigLoad 末尾补 AppCloudCfgSelect 带出槽位凭据 |
| V1.0.2.5 | 09-29 | 80c5650 | 【新增】每日闹钟掉电保存（gpio_tmr/tmrlv/tmrhh/tmrmm 四键）+ 定时面板 10s 无操作自动收起 |

## 版本号规范化前后（09-26 ~ 09-28，功能密集期）

| 日期 | 提交 | 内容 |
|------|------|------|
| 09-27 | 9287e0b | 版本号规则修订 |
| 09-27 | 3aac619 | 【新增】MQTT 协议转发（proto=3） |
| 09-28 | ea5ea08 / 996624c | 串口终端时间戳按行显示 + 毫秒 3 位 |
| 09-28 | 02b27f9 | STA 重连退避封顶 300s→60s |
| 09-28 | a4268b7 / a862de8 | GPIO 定时开关 → 重构为闹钟模式（ONCE 倒计时 + DAILY 每日）+ NTP 东八区对时 |

## 功能奠基期（09-26，版本号规范前）

| 提交 | 内容 |
|------|------|
| bed5e50 | 云平台配置分平台独立存储（分槽雏形） |
| 6a4f81a | 修复 OneNET 连接异常 |
| d999e04 | 修复网页连接状态与实际不同步 |
| 93ece11 | 串口波特率预设覆盖全部支持档位 |
| aea2cc2 / 2423784 | 串口终端多条发送 + 掉电保存 |
| ffcbf3f | 版本号命名规范 |
| 531b686 | 上电默认电平安全态 |
| c4f70b9 / 4510f71 | 按键开关延迟/异常修复 |
| 96a1544 | 全 GPIO 支持 PWM 输出 |
| 6222201 | 网页 GPIO 控制 |
| 181e151 | 按文档规范调整 |
| b669676 | 按键功能（FLASH 键手势） |
| fc4eb79 | 工程技能文档（Project_Level_Skill.md） |
| 83e4a3a / bab4346 | LED 实现调整 / 代码格式 |

## 云平台与稳定性攻坚期（09-22 ~ 09-23，stage 阶段号）

| 提交 | 内容 |
|------|------|
| b5c11b5 | 网页 WiFi 配网（AP 门户 + 扫描/连接/保存/重启） |
| 575ab91 | UART↔TCP/UDP 双向转发（阶段③） |
| c43c580 | STA+AP 双模常开，热点永不消失（stage3.3） |
| d4f0889 | 云平台透传：阿里云 IoT / OneNET（MQTT over TLS，stage4.0） |
| 7d681f6 | 巴法云接入（TCP/MQTT/MQTTS 三接入方式） |
| f320495 | 巴法 TCP 协议修正（cmd=1 订阅/ping 心跳/TLS 9503，官方文档核实） |
| 4277c53 | 删残留 DBG；云上行防饿死（静默 500ms 或满 1s 发批）；巴法界面精简 |
| cdb2f56 | MQTT CONNECT flags 0x02→0xC2（标准 broker 必拒修复，stage4.2） |
| cf6c35e | 首页 Cache-Control: no-store（浏览器旧缓存瘫页根治） |
| 56a8a27 | README 补充 |
| 4b77ef2 | CONNACK 解析修正（返回码在第 4 字节）；新增诊断字段 cloudtag/clouderr/cloudrc |
| 75166d7 | 网络重连指数退避 + HTTP 让路（网页优先，stage4.3） |

## 规划中（工程目标缺口）

- ~~HTTP 转发~~ ✅ V1.0.3.0 已完成；~~华为云 IoTDA~~ ✅ V1.0.5.0 已完成（**五大工程目标全部落地**）
- 各云平台控制台收发实测待真实凭据（华为/腾讯/阿里/OneNET；巴法 TCP 已实测）
