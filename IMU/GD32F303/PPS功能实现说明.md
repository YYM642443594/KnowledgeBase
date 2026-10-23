# PPS 功能实现说明（2026-10-23）

> 涉及文件：bsp_pps.h/c（驱动层）、bsp_parse.c（三接口配置）、bsp_data_interaction.c（推送分流）、
> bsp_function.c（配置纠错）、bsp_data_interaction.h（存储）、main.c（上电恢复）
> 适用工程：IMU_303_351 / IMU_103_303_333（共用 BSP_IMU.git 子仓库）

## 一、功能概述

PPS（秒脉冲）输入用于 IMU 时间戳校准与脉冲触发推送。三种模式：

| 模式 | 名称 | 行为 |
|------|------|------|
| 0 | 空 | 不校准、脉冲不触发推送 |
| 1 | 校准内部时间戳 | PPS 捕获回调实时同步校正系数，全部推送报文时间戳使用校准时间 |
| 2 | PPS 脉冲触发推送 | 数据推送由 PPS 脉冲沿触发（替代周期推送），推送内容由各通道总开关 PushStatus 决定 |

## 二、配置接口（三接口，谁配置谁生效来源）

三个物理接口配置**同一组**全局 PPS 开关/模式：

| 接口 | 指令/报文 | 开关 | 模式 |
|------|-----------|------|------|
| AT 文本 | `AT+PPS=ON/OFF`、`AT+PPSMODE=n`、`AT+PPS?`、`AT+PPSMODE?` | PPSStatus | PPSMode |
| HEX 报文 | 0x0012（Op=0x00 查询/0x01 设置/0x02 设置并保存） | PPSStatus | PPSMode |
| CAN 报文 | 0x109（Data[0]=0x00 查询/0x01 设置/0x02 设置并保存；Playload[0]=模式 [1]=锁定 [2]=开关） | PPSStatus | PPSMode |

- 模式值域 0~2，开关值域 0/1，`BspDefaultCfgCheck()` 白名单纠错（非法归 0）
- 查询类指令各自回显当前全局 PPSStatus/PPSMode，0x109 额外回显锁定状态

## 三、模式 1：时间戳校准原理

### 3.1 校正模型

```text
校准时间(us) = 原始运行时间 × G_SlopeA(频偏斜率) + G_SkewingB(整秒对齐偏移)
```

- 每个有效 PPS 脉冲沿进入 `BspPPS1SCallback()`：DWT 捕获原始时间 → 与上一次捕获差分、
  绝对整秒递推，最小二乘/均值方式修正 `G_SlopeA` 与 `G_SkewingB`
- 未同步前系数为初值（斜率 1/偏移 0），校准输出与原始运行时间一致——无跳变风险
- 信号锁定跟踪：2s 无脉冲判失锁（`BspPPSLockStatusGet()`），0x109/0x0013 可查询

### 3.2 时间戳注入点（全局生效）

`BspPushTimestampGet()`（bsp_data_interaction.c）为全部推送报文（上位机 3D/原始、
AT、HEX 各包、CAN 完整流/精简流）的统一时间戳源：

```c
if (BspPPSStatusCtrlGet() == 1 && BspPPSModeGet() == 1)
    return BspPPSCalibratedUsGet();   /* 任一接口把PPS配为模式1即全局校准 */
return BspSysRunTimeGet();
```

### 3.3 关闭/切换行为

- 关闭 PPS（或切换模式）**不重置** G_SlopeA/G_SkewingB/G_PPPS_TC_Last：
  校准时间按最后斜率平滑外推，时间戳单调连续不跳变；重新开启无需重新同步
- 所有通道关闭时 `BspPPSStatusCtrlSet(0)` 复位信号锁定状态
- 全部关闭时回调直接 return，忽略引脚毛刺（防插拔导致时间戳跳变）

## 四、模式 2：PPS 脉冲触发推送

### 4.1 计数器消费机制

```text
EXTI 捕获回调(BspPPS1SCallback, 中断上下文)
  └─ 任一通道 PPS 开启时 G_PPSTriggerCount++ (volatile, 饱和防溢出)
主循环 BspUserDataPushControlCenter()(每圈轮询)
  ├─ 门控: BspPPSModeGet()==2 && BspPPSStatusCtrlGet()==1
  ├─ TrigCnt = BspPPSTriggerConsume(1)   ← 每圈最多消费 1 轮
  └─ 按 PushStatus 推送全部开启通道(见 4.2)
```

- **计数器而非单 bit 标志**：主循环两圈之间到来的多个脉冲不丢失，高频 PPS（~700Hz）
  推送率可跟随输入，积压下圈补推
- **每圈上限 1 轮**：一轮含 AT 帧串口忙等（~2.6ms）或 HEX 全包/CAN 两流入队，
  耗时较大，防拖长单圈
- **先无条件消费**：关闭/切换期间残留脉冲被清掉，条件恢复时不凭空多推
- 模式 2 进出边界（`BspPPSModeSet()` 内检测）清残留计数，防切换后旧脉冲推新帧
- 组包/发送仍在主循环上下文，与周期推送/应答帧无重入冲突

### 4.2 推送内容（各通道总开关决定）

模式 2 激活期间三通道周期推送**全部停止**（`TrigMode2Active` 门控），
脉冲触发推送全部总开关开启的通道：

| 通道 | 脉冲触发推送 | 总开关 |
|------|-------------|--------|
| AT | 一帧 AT 数据 | `UserATDataPushCfg.PushStatus` |
| HEX | 全部已订阅包（0x0001/0002/0010/0013/0022，另受各包订阅位约束） | `UserHexDataPushCfg.PushStatus` |
| CAN 完整流 | 完整流数据 | `UserCanDataPushCfg.PushStatus` |
| CAN 精简流 | 精简流数据 | `UserCanSimpDataPushCfg.PushStatus` |

- 各通道独立开关独立生效：开着哪个推哪个，全关时脉冲无物可推（设备静默属用户主动配置）
- 上位机 3D/原始数据为独立通道，不受模式 2 控制（维持周期推送，仅时间戳受模式 1 校准）
- 模式 2 退出后周期推送立即恢复（LastPushTick 已过阈值，无需额外处理）

### 4.3 MSGID 订阅控制（HEX 包级开关）

HEX 各包（0x0001/0002/0010/0013/0022）订阅位 `DataPacket0x00XX:1` 由三处控制：
CAN 0x104（MsgID 控制）、HEX 0x0011、AT 订阅指令。

**关键实现**：`BspPushUserHexData()` 的订阅判定读 **shadow（运行态镜像）** 而非
工作副本：

```c
pProductInfo_S pSub = BspProductInfoShadowGet();
if (pSub->DataPacket0x0001 == 1) { BspPushSensorDataToUser_0x0001(); } ...
```

原因：0x104/0x0011 的 **Op=0x01（写 RAM，掉电不保存）路径只更新 shadow**，
读 shadow 才能即时生效；Op=0x02（写 Flash）两者同步写，行为一致。
开机时 `BspSyncProductInfoToShadow()` 保证 shadow 与 Flash 配置对齐。

> 已知遗留：推送总开关 PushStatus（0x103/0x0004 等）的 Op=0x01 路径同样只写 shadow，
> 调度层仍读工作副本，属既有行为，未统一。

## 五、存储与兼容

### 5.1 预留区与字段回退记录

预留区 100B 当前**未启用任何字段**。曾实现过 `PPSSwitchType`（u8，记录 PPS 开关
来源接口 1:AT 2:HEX 3:CAN，用于模式 2 单通道分流）——声明于 `UserCanSimpDataPushCfg`
与 Reserved 之间（Reserved 100B→99B，sizeof 恒 204B）。后该方案回退删除，
Reserved 恢复 100B：

- 回退原因：模式 2 推送语义最终定为"各通道总开关 PushStatus 独立决定"，无需来源记录
- **回退兼容性**：删 1B 字段 + Reserved +1B 相互抵消，sizeof/CRC 长度不变，
  旧格式页迁移不受影响；曾保存过 SwitchType 的设备该字节落在新固件 `Reserved[0]`，
  不读不校验，无需处理
- 经验：字段引入/删除只要始终"在注释与 Reserved 之间声明 + 同步增减 Reserved 字节数"，
  即可保证任何版本间双向兼容
- 预留区规程（见《参数页升级SN乱码与预留区扩展机制报告》）：

```text
新增字段 = 在注释与 Reserved 之间声明 + Reserved 减对应字节数 + 维护分配表
新字段默认值必须为 0 语义；多字节字段放 4 对齐偏移；
禁止改动现有字段顺序/类型；禁止在预留区之前插入字段
```

### 5.2 上电恢复

main.c 初始化段从配置恢复运行态（否则上电后 PPS 运行态始终为关闭）：

```c
BspPPSStatusCtrlSet(pProductInfoShadow->PPSStatus);
BspPPSModeSet(pProductInfoShadow->PPSMode);
```

## 六、0x0013 报文说明

0x0013 为 PPS 状态报文：`PPSStatus` 字段填锁定状态（`BspPPSLockStatusGet()`）、
`PPSMode` 填全局模式；时间戳恒用校准时间（`BspPPSCalibratedUsGet()`）。
其推送归属：模式 2 激活时随 HEX 通道其它已订阅包一并由脉冲触发；
非模式 2 时保持周期推送（回退语义）。

## 七、实现避坑清单

| # | 要点 |
|---|------|
| 1 | 模式 2 消费点门控用运行态接口（`BspPPSStatusCtrlGet/BspPPSModeGet`），勿读工作副本——Op=0x01 设置路径不同步工作副本 |
| 2 | `BspPPSModeSet()` 内做模式 2 进出边界清计数，切换模式不残留旧脉冲 |
| 3 | 0x0013 在 `BspPushUserHexData` 内直接推（周期/脉冲两入口互斥不双发，由调度层 TrigMode2Active 门控保证） |
| 4 | HEX 订阅判定读 shadow，保证 MSGID 指令 Op=0x01 写 RAM 即时生效 |
| 5 | AT 指令字符串比较用 `sizeof("AT+PPSMODE?")-1`，防止 "AT+PPSMODE?" 被 "AT+PPSMODE=" 前缀分支截获 |
| 6 | AT 关键应答使用 `BspParseSendDataWait` 等发送缓冲空闲，防数据交织 |
| 7 | PPS 信号消抖窗口 1ms（支持至 700Hz 输入）；全通道关闭时回调忽略脉冲防毛刺 |
| 8 | AT 推送帧内含时间戳回退检测（`BspPushUserATData` 开头，检测原始时基回退自动停推）：检测用原始时基、输出用统一时间戳源（模式 1 为校准时间），两源整秒对齐存在 ≤1s 相位差，勿跨源比较否则模式切换瞬间会误触发停推 |
