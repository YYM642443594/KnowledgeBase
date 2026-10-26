# 04 协议层模块 bsp_uart_protocol

> 源码：[Code/bsp_uart_protocol.c](../Code/bsp_uart_protocol.c) / [Code/bsp_uart_protocol.h](../Code/bsp_uart_protocol.h)

## 定位

志翔 IMU 串口私有协议层：帧同步状态机 + CRC16 校验 + 帧级统计 + 数据包1/2/3/4 解析 + 设备时间戳Δt统计。纯函数+内部静态状态，与平台无关。

## 帧格式与 CRC16

```text
AA 55 | CMD | ID | LEN_L LEN_H | DATA... | CRC_L CRC_H
```

- **LEN 为整帧长度**（帧头 6 字节 + 数据域 + CRC 2 字节），数据域长度 = LEN − 8，多字节字段小端（intel）
- **CRC16**：初值 `0x3692`、多项式 `0x8408`（反向 LSBF），计算范围 = 帧头至数据域末字节（不含 CRC 本身）。`BspUartCrc16(pBuf, n)` 独立导出，AT/HEX 验证器同算法参考

## 帧同步状态机（7 状态）

```text
WAIT_SYNC1(0xAA) → WAIT_SYNC2(0x55) → WAIT_CMD → WAIT_ID → WAIT_LEN_L → WAIT_LEN_H → PAYLOAD(整帧长-6字节)
```

- 逐字节喂入（`BspUartProtocolOnByte`），任一环节不符合即回退重同步（SYNC2 不符退回重找 0xAA）
- 进入 PAYLOAD 前校验 LEN 合法性（`LEN-8` 是否落在数据域容量内），非法长度帧直接剔除
- 帧收完后 CRC 校验：**只统计校验通过的帧**；坏帧/垃圾字节不影响后续帧同步（帧间夹噪声自动剔除）
- 状态机同时累计 `FeedBytes`（喂入字节数）与 `CrcFail`（CRC 失败帧数）两个诊断计数

## 帧级统计（与 CAN 分支字段对齐）

每个报文 ID 独立维护 `UartFrameStat_S`：

| 字段 | 含义 |
|------|------|
| Count | 累计帧数（CRC 通过） |
| 平均Hz | (Count−1) ÷ (末帧时刻−首帧时刻)，全程平均 |
| InstHz / WinStart / WinCount | 瞬时Hz：1 秒滑动窗口 |
| LastIntMs / MinIntMs / MaxIntMs / SumInt | 帧间隔：当前/最小/最大/累计求平均 |

统计对象：数据包1（0x0001，87 字节）/ 数据包2（0x0010，44）/ 数据包3（0x0013，105）/ 数据包4（0x0022，38），`UART_MSG_NUM=4`，ID→下标映射 `MsgIndex()`。

**判读参考**：50Hz 推送 → 平均间隔 ≈ 20.0ms；最大ms 无大跳 → 流稳定无断流；最小 1ms 级毛刺/最大百万毫秒级跳变 → 设备侧丢帧或时间戳异常。

## 设备时间戳Δt统计（数据包2/3/4）

`UartTsDelta_S`：相邻帧设备 us 时间戳之差的 最新/平均/最小/最大/样本数。

- 与 CAN 分支 0x091 同语义：**全样本无过滤**——时间戳回退、重置、乱序不丢弃，直接体现在极值（最小可能为负/接近 0，最大百万 ms 级），异常即证据，不做静默吞掉
- `TsOffset(Id)` 按报文 ID 定位数据域内时间戳字段偏移，无时间戳的数据包1 不参与

## 数据包解析（最新帧物理量）

每包独立解析函数（`ParseData1/2/3/4`），小端逐字段取出，存入 `UartFrameStat_S.LastData` 对应结构：

| 数据包 | ID | 数据域 | 内容 |
|--------|----|--------|------|
| 1 | 0x0001 | 87B | 频率/日期时间/加计XYZ+模长/陀螺XYZ+模长/温度/姿态RPY/四元数/磁场 |
| 2 | 0x0010 | 44B | 时间戳us/加计XYZ/陀螺XYZ/姿态RPY |
| 3 | 0x0013 | 105B | 数据包1 全集 + 时间戳us + PPS锁定与模式 + 预留 |
| 4 | 0x0022 | 38B | 时间戳us/加计XYZ/陀螺XYZ |

自检要点：加计静止模长 ≈ 9.8 m/s²、四元数模长 ≈ 1、温度常温 20~40℃。

## 对外接口

| 函数 | 说明 |
|------|------|
| `BspUartProtocolOnByte` | 喂 1 字节，返回 1=完成一帧且 CRC 通过 |
| `BspUartProtocolGetMsgId/GetStat/GetTsDelta` | 按 Index(0~3) 只读获取 ID/统计/Δt统计 |
| `BspUartProtocolGetCrcFail / GetFeedBytes` | 诊断计数 |
| `BspUartProtocolPrintStat(ElapsedSec, Tty)` | 打印统计表+各包最新解析值+Δt行 |
| `BspUartCrc16` | CRC16 算法导出 |

## 终端原地刷新机制

打印块固定 `UART_STAT_PRINT_LINES=31` 行（表头2+统计表4+空行+解析表头+4包解析20行+Δt 3行）：终端模式（Tty=1）每秒打印后光标回退 31 行原位覆盖重绘，配合 `\r` 起始+清行尾（`\033[K`）防止长行残留顶乱表格列；管道模式（Tty=0）退化为 5 秒全量打印，便于重定向留档。
