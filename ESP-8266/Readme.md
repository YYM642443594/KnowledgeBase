# ESP8266-XCOM 串口 WiFi 透传器 工程记录

- **MCU**：ESP8266（NodeMCU v2 板载 CH340 USB 转串口，仅 2.4GHz WiFi）
- **SDK**：PlatformIO + Arduino 框架（env: `nodemcuv2`，LittleFS）
- **定位**：串口↔WiFi 双向透传 + 物联网云桥（设备串口数据上云，云下行写回串口）
- **仓库**：`git@github-esp8266:YYM642443594/ESP8266.git`（master/develop 同步于 stage4.2, 56a8a27）
- **当前版本**：stage4.2

## 功能总览

| 模块 | 说明 |
|------|------|
| 基础透传 | TCP/UDP 服务端(:8344) ↔ 串口双向；客户端转发模式（网页配置目标 IP:PORT） |
| 网络架构 | AP+STA 双模常开（热点 `ESP8266-XCOM-xxxx` @192.168.4.1 永不掉线），全异步不阻塞 loop |
| 云平台 | 巴法云(TCP 8344/MQTT 9501/MQTTS 9503)、阿里云 IoT(TLS 8883)、OneNET(TLS 8883) |
| 网页门户 | 192.168.4.1 单页四标签：配网/串口终端/转发/物联网平台 |

## 目录结构

```text
src/
├── main.cpp      ← 路由/状态机/串口透传/WiFi守护
├── web_page.h    ← 单页门户 (PROGMEM, 4标签, 动态表单)
└── cloud.h       ← 云抽象层 (~500行, 手工MQTT + TLS)
```

## 关键实现决策

- **手工组 MQTT 报文**（CONNECT/SUBSCRIBE/PUBLISH QoS0），不引 PubSubClient/ArduinoJson —— 省堆内存（省 ~10KB+）
- TLS：BearSSL `setInsecure()` + `setBufferSizes(256,512)`；显式状态机解析，`available()` 门控防 TCP 分段错位
- 上行队列：1024B 环形，**发布条件 = 静默>500ms 或 距上次>1s**（用"且"会在持续流式数据下永久饿死——实测教训）
- 巴法 TCP 订阅应答 `cmd=1&res=1` 收到才置"在线"，防止假连接
- MQTT CONNECT flags 必须 **0xC2**（clean session+username+password；0x02 缺声明位会被标准 broker 拒连）
- 首页必须发 `Cache-Control: no-store`，否则固件升级后浏览器缓存旧 JS 会使整页瘫掉

## 资源水位

- RAM 45.9% / Flash 47.9%
- 稳态空闲堆 ~25KB；开机瞬态可到 12KB（WiFi/DHCP/mDNS/云并发，非泄漏）

## 构建与烧录

```bash
pio run                                        # 编译
pio run -t upload --upload-port /dev/ttyUSB0   # 烧录（先查占用 lsof /dev/ttyUSB0）
```

- 配置存 LittleFS `config.txt`；erase_flash 即出厂
- 烧录断串口后需重启上位机串口脚本（serial_sim.py）
- 验证：连热点 → `curl http://192.168.4.1/api/status`；`curl -I`(HEAD) 返回 404 属正常（固件只注册 GET）

## 已知限制 / 待办

- TLS 不验证书链（板子无 RTC 无法校时间），传输仍加密，存在理论中间人风险
- MFLN 探测未做（固定 256/512 缓冲）
- OneJSON/物模型包装未做：云上收发为串口原始字节
- 巴法 MQTT(9501) 已端到端实测在线（2026-09-23）；MQTTS(9503) 未实测——**巴法 TCP 主题与 MQTT 主题是两套独立控制台体系**，MQTT 接入需另建主题
- 阿里云/OneNET 待真实凭据端到端验证

## 踩坑记录

| 坑 | 教训 |
|----|------|
| brltty 抢占 CH340 (1a86:7523) | Ubuntu 经典 bug，`apt remove brltty` + mask brltty-udev |
| AP "时隐时现" | 同步 scanNetworks 阻塞 2-3s 停 beacon；改异步扫描 |
| 板子"消失" | 旧版 STA 连上即关 AP；双模常开根治 |
| 上行"看不到数据" | ①模拟脚本没重启 ②发布条件"且"饿死流式数据 |
| 假在线 | 巴法订阅 cmd 码写错 + 发完就置已连接；**协议必须抓官方文档，不能凭记忆猜** |
| 网页整页瘫 | 浏览器缓存旧页 JS 与新固件 DOM 不匹配；服务端发 no-store 根治 |

云平台协议速查（巴法 cmd 表 / 阿里云 / OneNET 签名格式）见 [Cloud_Protocol.md](Cloud_Protocol.md)。
