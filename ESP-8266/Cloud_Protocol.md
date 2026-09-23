# 物联网云平台接入协议速查

> 来源：巴法官方文档（cloud.bemfa.com/docs/src/）实测核实 + 阿里云/OneNET 官方签名规范。
> 2026-09 巴法接入调试中沉淀；巴法 TCP 模式已端到端实测，其余待实测。

## 巴法云 bemfa.com

### TCP 8344（文本协议，键值对 `&` 分隔，`\r\n` 结尾）

| 指令 | 报文 | 应答 |
|------|------|------|
| 订阅 | `cmd=1&uid={私钥}&topic={主题}\r\n` | `cmd=1&res=1` 才算成功 |
| 发布 | `cmd=2&uid={私钥}&topic={主题}&msg={URL编码}\r\n` | `cmd=2&res=1` |
| 订阅+拉历史 | `cmd=3&uid=&topic=\r\n` | 回推保留消息 |
| 取时间 | `cmd=7&uid=\r\n` | |
| 拉历史 | `cmd=9&uid=&topic=\r\n` | |
| 心跳 | 任意 `\r\n` 结尾数据，推荐 `ping\r\n` | `cmd=0&res=1` |

要点：
- **res=1 = 成功，res=0 = 失败/重复**（勿凭直觉反着猜）
- 心跳周期：65s 不发即掉线（建议 25s）
- 多主题订阅：topic 逗号分隔，≤8 个
- 主题后缀语义：`/set` 群发（不回推给自己）；`/up` 只存云端不推送；`/app` 订阅不计入设备在线
- 下行推送格式：`cmd=3&uid=&topic=&msg=...`（兼容解析：行内搜 `&msg=`）
- **TCP 主题在 TCP 控制台建，与 MQTT 控制台主题互不相通**

### MQTT

- 端口：**9501 明文 / 9503 TLS(不是9502) / 9504 wss(path /wss)**
- 认证：clientId = uid(私钥) 即可；user/pass 随意（不存在鉴权绑定）
- 能力：QoS0/1 + retain；**QoS2 会被强制下线**（多次可致账号异常）
- `clientId` 错误时降级用 user/pass 鉴权（user=appID, pass=secretKey）

## 阿里云 IoT（TLS 8883，固件已实现未实测）

- username = `{DeviceName}`
- password = `base64( hmac_md5(DeviceSecret, "productKey{pk}&deviceName{dn}&timestamp2524576000000&") )`
  - 时间戳为固定值（免 RTC 方案）
- 默认透传主题：`/{pk}/{dn}/data`（需在控制台建，发布+订阅权限）
- 企业版实例接入域名不同，需自填 host
- 三元组 = ProductKey / DeviceName / DeviceSecret

## OneNET（MQTT over TLS 8883，固件已实现未实测）

- token 鉴权：version `2018-10-31`，res=`products/{pid}/devices/{dn}`，et=`4102444800`，method=md5
- 签名密钥 = **AccessKey 先 base64 解码**再 HMAC-MD5（不是直接用字符串）
- payload 为原始字节（OneJSON 物模型未实现，接物模型需另加包装层）
- 三元组 = 产品ID / 设备名 / AccessKey

## 通用 MQTT 底层备忘（手工组包）

- CONNECT 可变头：`MQTT`+\x04（3.1.1），flags **0xC2** = clean session + username + password 三位必须随 payload 声明，keepalive 60s
- 订阅/发布走 QoS0 最简路径；解析用显式状态机（HDR→LEN→TOPIC→PAYLOAD），每字节 `available()` 门控防 TCP 分段撕裂
- ESP8266 上 BearSSL：`br_hmac_key_init(&kc,&br_md5_vtable,key,len)` → `br_hmac_update` → `br_hmac_out`（16B）
