# AT / HEX / CAN 指令集说明（2026-10-23）

> 工程：IMU_303_351（GD32F303，共用 BSP_IMU.git 子仓库）
> 源码：bsp_parse.c 三张指令表 `G_BSPATParseCMD` / `G_BSPHexParseCMD`（含 `G_BSPParseCMD` 生产标定区）/ `G_BSPCANParse`
> 关联文档：《PPS功能实现说明.md》《参数页升级SN乱码与预留区扩展机制报告.md》

## 一、AT 指令（串口文本，\r\n 结尾，回显式应答）

| 指令 | 功能 | 备注 |
|------|------|------|
| `AT+VERSION?` | 查询固件版本 | 应答使用 `BspParseSendDataWait` 等发送缓冲空闲，防数据交织 |
| `AT+BAUD=<n>` / `AT+BAUD?` | 设置/查询串口波特率 | 保存后重启生效 |
| `AT+SET=ON/OFF` / `AT+SET?` | AT 数据推送开关设置/查询 | 控制 `UserATDataPushCfg.PushStatus` |
| `AT+PUSHFRQ=<ms>` | AT 数据推送频率 | 控制 `UserATDataPushCfg.DataPushFre` |
| `AT+MSGID=<n>,<0/1>` | HEX 数据包订阅控制 | n=1/2/10/13/22 对应 0x0001/0002/0010/0013/0022 包；写 shadow+工作副本并落盘 |
| `AT+COORDINATE?` / `AT+COORDINATE=<n>` | 查询/设置坐标系统 | |
| `AT+PPS=ON/OFF` / `AT+PPS?` | PPS 开关设置/查询 | 开启置 `PPSSwitchType=1`（AT 来源），关闭归 0；落盘 |
| `AT+PPSMODE=<0/1/2>` / `AT+PPSMODE?` | PPS 模式设置/查询 | 0:空 1:校准内部时间戳 2:PPS脉冲触发推送 |
| `AT+CANBAUD=<n>` | CAN 波特率设置 | |
| `AT+SN?` | 查询 SN 号 | |
| `AT+ZEROBIASCAL` | 零偏校准 | 置 `ZeroBiasCalibration` 标志并落盘 |
| `AT+DATATIME?` | 查询数据时间 | |
| `AT+DATALINK=<n>` | 数据链路与开关状态配置 | **Buf[7]=0x00 一键关闭四路推送**（AT/HEX/CAN 完整流/CAN 精简流）；=0x03 时精简流频率同步完整流频率 |
| `AT+GRAPHRQ=<ms>` | 主图 3D 数据推送频率 | 与 `AT+ORIGRQ` 同处理器分发 |
| `AT+ORIGRQ=<ms>` | 原始数据推送频率 | |
| `AT+ACCSCALECFG=<n>` | 加速度量程配置/查询 | 白名单校验 |
| `AT+GYROSCALECFG=<n>` | 角速度量程配置/查询 | |
| `AT+FLASHCFG` | 查询 Flash 存储的全部配置 | A/B 双页 dump：序号、CRC、SN、各配置项、PPS switchType；区分 OK/OK(legacy)/BAD |
| `AT+FLASHPROTECT=<0/1>` | Flash 写保护开关 | |
| `AT+YAWRESET` | YAW 角归零重置 | |
| `AT+RST` | 设备重启 | |
| `AT+CMD` | 查询全部 AT 指令列表 | 自描述 |
| `AT+CONFIG` | 查询配置参数汇总 | |

## 二、HEX 指令（串口二进制帧）

### 2.1 帧格式

```text
AA 55 | CMD | ID | Op | LenL LenH | Data... | CRC16L CRC16H
```

- CRC16 校验，小端；`Len` 不含 CRC，上限 255
- `Op`：0x00=查询 0x01=设置（仅 RAM，掉电不保存，运行态即时生效）0x02=设置并保存（Flash）
- 应答帧使用 `BspBuildUserReplyDataPackaging(SEND_CMD_0X00_E, 同ID, ...)` 回包

### 2.2 用户配置指令（CMD=0x00）

| ID | 处理器 | 功能 |
|----|--------|------|
| 0x03 | `BspVersionGet_0003` | 版本查询（应答 8B） |
| 0x04 | `BspPushFreSet_0004` | HEX 推送频率设置（PushStatus + DataPushFre，Op=0x01 仅写 shadow） |
| 0x05 | `BspReviseBleName_0005` | 修改蓝牙名称（Data 16B） |
| 0x06 | `BspAlgorithmMode_0006` | 算法模式设置/查询 |
| 0x07 | `BspUserDataSwitch_0007` | HEX 推送总开关（`UserHexDataPushCfg.PushStatus`） |
| 0x11 | `BspUserPushDataPackCtrl_0011` | 数据包订阅控制（包 ID 0x0001/0002/0010/0013/0022 逐包开关，即 HEX 侧 MSGID 控制） |
| 0x12 | `BspPPSSwitchCtrl_0012` | PPS 控制（查询/开关/模式；开启置 `PPSSwitchType=2`） |
| 0x14 | `BspDevRst_0014` | 设备重启 |
| 0x15 | `BspSetCoordinateSystem_0015` | 坐标系统设置（应答 10B） |
| 0x16 | `BspUartRate_0016` | 串口波特率设置/查询 |
| 0x17 | `BspCanRate_0017` | CAN 波特率设置/查询 |
| 0x18 | `BspQuerySN_0018` | 查询 SN 号（应答 24B） |
| 0x19 | `BspModificationDataTime_0019` | 修改数据时间（应答 8B） |
| 0x20 | `BspZeroCalibration_0020` | 零偏校准 |
| 0x21 | `BspYawReset_0021` | YAW 角归零重置（应答 9B） |
| 0x22 | `BspHexScaleCfg_0022` | 加速度/角速度量程配置（应答 10B） |

### 2.3 其它 HEX 指令

| CMD | ID | 功能 |
|-----|-----|------|
| 0x01 | 0x01 | A 值查询 |
| 0x01 | 0x03 | 电池状态查询 |

### 2.4 生产/标定指令（`G_BSPParseCMD`，产测工装/上位机使用）

| CMD | ID | 功能 |
|-----|-----|------|
| 0x01 | 0x10 / 0x12 / 0x15 / 0x21 | 单板测试广播 / 温标测试 / 数据采集 / 单板测试写入 SN |
| 0x04 | 0x17 / 0x18 / 0x19 | 转台标定 / 下载转台参数 / 下载温漂参数 |
| 0x05 | 0x00 / 0x01 / 0x02 / 0x06 / 0x0B / 0x0C | 设备复位 / 主图数据推送控制 / 原始数据刷新控制 / 加速度校准 / 获取参数 / 设置参数 |
| 0x06 | 0x01~0x09 | 设置硬件号 / 设置 SN / 打开串口 / 进入升级模式 / 查询电池电量 / 修改蓝牙名称 / 磁力计校准 / 硬件号查询 / YAW 归零 |
| 0x07 | 0x01 | 设置 A 值 |
| 0x08 | 0x01 / 0x02 | 标定台控制 / 标定台温控 |

## 三、HEX 数据推送包（设备 → 上位机，SendCmd=0x00 + SendID）

| SendID | 包结构 | 内容 |
|--------|--------|------|
| 0x0001 | `PushUserData0x0001_S` | 传感器数据包（姿态等） |
| 0x0002 | 2B | 状态包 |
| 0x0010 | `PushUserData0x0010_S` | 扩展数据包 |
| 0x0013 | `PushUserData0x0013_S` | PPS 状态包：锁定状态 + PPSMode + 校准时间戳（时间恒用 `BspPPSCalibratedUsGet()`） |
| 0x0022 | `PushUserData0x0022_S` | 量程数据包 |

推送行为：各包按订阅位（`DataPacket0x00XX`）与 HEX 通道总开关（0x0004 PushStatus + DataPushFre）周期推送；PPS 模式 2 且 `PPSSwitchType=2` 时改由脉冲触发（详见《PPS功能实现说明.md》）。订阅位受 0x0011（HEX）、CAN 0x104、AT+MSGID 三处控制，推送判定读 shadow 运行态镜像（Op=0x01 即时生效）。

另有主图 3D / 原始数据独立推送帧（SendCmd 0x04~0x07 系，`BspBuildRadioResponse` 组包），不受 HEX 包订阅控制，仅受各自 PushStatus/频率与 PPS 模式 1 时间戳校准影响。

## 四、CAN 指令（CAN ID 0x100~0x115，8 字节数据）

| CAN ID | 处理器 | 功能 |
|--------|--------|------|
| 0x100 | `BspCanVersion_100` | 版本查询 |
| 0x101 | `BspCanPushFreq_101` | 推送频率配置（同时作用于完整流与精简流，二者保持同频） |
| 0x102 | `BspCanIMUCoordinate_102` | IMU 坐标系设置/查询 |
| 0x103 | `BspCanDataStreamStatus_103` | 数据流（完整流）推送开关；Op=0x01 仅写 shadow |
| 0x104 | `BspCanMsgIDCtrl_104` | MSGID 控制：子 ID 0x01/02/10/13/22 逐包订阅 HEX 数据包 |
| 0x105 / 0x106 | `BspCanSNLow8_105` / `BspCanSNHeigh8_106` | SN 低 8 字节 / 高 8 字节查询 |
| 0x107 | `BspCanRate_107` | CAN 波特率设置/查询 |
| 0x108 | `BspUARTBaudRate_108` | 串口波特率设置/查询 |
| 0x109 | `BspPPSCtrl_109` | PPS 控制（Playload[0]=模式 [1]=锁定 [2]=开关；开启置 `PPSSwitchType=3`） |
| 0x110 | `BspDevRst_110` | 设备重启 |
| 0x111 | `BspZeroBiasCalibration_111` | 零偏校准 |
| 0x112 | `BspYawReset_112` | YAW 角归零重置 |
| 0x113 | `BspUARTCtrl_113` | UART 串口开关控制 |
| 0x114 | `BspUserCanSimpDataPushCfg_114` | 精简数据流（原始数据）推送开关（仅开关；频率统一由 0x101 管理） |
| 0x115 | `BspCanScaleCfg_115` | 加速度/角速度量程配置 |

## 五、三接口配置语义对照（PPS 与推送开关）

| 配置项 | AT | HEX | CAN | 存储字段 |
|--------|-----|------|------|----------|
| PPS 开关 | AT+PPS=ON/OFF | 0x0012 | 0x109 | PPSStatus（PPSSwitchType=1/2/3 记录来源） |
| PPS 模式 | AT+PPSMODE | 0x0012 | 0x109 | PPSMode（0/1/2） |
| 推送总开关 | AT+SET（AT 路）/ AT+DATALINK（四路） | 0x0004 / 0x0007 | 0x103 / 0x114 | UserATDataPushCfg / UserHexDataPushCfg / UserCanDataPushCfg / UserCanSimpDataPushCfg 的 PushStatus |
| 推送频率 | AT+PUSHFRQ / AT+GRAPHRQ / AT+ORIGRQ | 0x0004 | 0x101（完整+精简同频） | 对应 DataPushFre |
| 包订阅 | AT+MSGID | 0x0011 | 0x104 | DataPacket0x0001/0002/0010/0013/0022 |

**通用规则**：设置类 Op=0x01（HEX）/未带保存标志（CAN）只写 shadow（运行态即时生效，掉电不保存）；Op=0x02 写 shadow+工作副本并 `BspProductInfoSaveToFlash()`（延迟落盘）；查询类 Op=0x00 回显 shadow 当前值。
