# `IMU Linux` 串口验证程序 (Linux-UartTestVerifDemo)

> 2026-10-26 归档：源工程 `IMUDemo`（分支 `feature/LinuxUartTestVerifDemo`），Linux 上位机侧的志翔 IMU 示例 Demo 与自测试程序。单可执行 `imu_test`，参数选择三大功能。本目录整理**各模块的功能实现**（Doc/）并快照源码（Code/）。

## 工程定位

| 属性 | 说明 |
|------|------|
| 平台 | Linux PC（gcc + pthread，无第三方依赖） |
| 对象 | 志翔 IMU 设备（串口，志翔私有协议，默认 921600 8N1） |
| 形态 | 单可执行 `imu_test`，参照 `feature/LinuxCanTestVerifDemo` 分支的三层架构（驱动/队列/协议）与统计方式 |
| 版本 | V1.7.8（2026-10-22，详见 [Doc/07](Doc/07-主入口与构建运行.md) 版本史与源工程 Readme） |

## 三大功能（示例 Demo + 自测试程序）

| 功能 | 名称 | 内容 | 模块 |
|------|------|------|------|
| 1（默认） | 数据流统计 | 接收推送报文，数据包1/2/3/4 帧级统计（帧数/平均Hz/瞬时Hz/帧间隔极值）+ 最新帧物理量解析 + 设备时间戳Δt统计，验证帧率/断流/解析正确性 | bsp_uart_protocol + main |
| 2 | AT 指令验证 | 依据《用户协议》第2章 40 条用例逐条下发，按文档应答格式判定，配置自动还原 | bsp_at_test |
| 3 | HEX 协议验证 | 依据《用户协议》第3.2章 19 个报文 ID 逐 ID 验证（32 条用例含异常组），另有压力/暴力模式（fuzz 轰炸/截断恢复等 5 项） | bsp_hex_test |

## 模块导航（功能实现文档）

| 文档 | 模块 | 要点 |
|------|------|------|
| [01-架构与线程模型](Doc/01-架构与线程模型.md) | 总体设计 | 三层架构、SPSC 双线程流水线、优雅退出 |
| [02-串口驱动](Doc/02-串口驱动模块-drv_serial.md) | drv_serial | termios 原始模式 8N1、八档波特率、ASYNC_LOW_LATENCY |
| [03-环形队列](Doc/03-环形队列模块-bsp_uart_queue.md) | bsp_uart_queue | 4KB SPSC 无锁环形队列、满丢弃计数 |
| [04-协议层](Doc/04-协议层模块-bsp_uart_protocol.md) | bsp_uart_protocol | 帧同步状态机、CRC16、帧级统计、数据包1~4解析、Δt统计 |
| [05-AT指令验证](Doc/05-AT指令验证模块-bsp_at_test.md) | bsp_at_test | 用例表驱动、混流容错（剔帧+双条件判定）、成对自动还原 |
| [06-HEX协议验证](Doc/06-HEX协议验证模块-bsp_hex_test.md) | bsp_hex_test | 19 ID 全覆盖、查询缓存动态还原、异常组、压力模式 |
| [07-主入口与构建运行](Doc/07-主入口与构建运行.md) | main.c / run.sh | 功能分发、参数解析、一键编译菜单脚本 |

## 目录结构

```text
Linux-UartTestVerifDemo/
├── Readme.md                ← 本索引
├── Doc/                     ← 各模块功能实现文档
│   ├── 01-架构与线程模型.md
│   ├── 02-串口驱动模块-drv_serial.md
│   ├── 03-环形队列模块-bsp_uart_queue.md
│   ├── 04-协议层模块-bsp_uart_protocol.md
│   ├── 05-AT指令验证模块-bsp_at_test.md
│   ├── 06-HEX协议验证模块-bsp_hex_test.md
│   └── 07-主入口与构建运行.md
└── Code/                    ← 源码快照（与源工程 00.Code/ 一致）
    ├── main.c               统一入口：功能分发 + 统计主循环、线程管理
    ├── drv_serial.c/h       串口驱动模块（termios，8N1，低延迟）
    ├── bsp_uart_queue.c/h   字节流 SPSC 环形队列（4KB）
    ├── bsp_uart_protocol.c/h 协议层：帧同步/CRC16/统计/数据包1~4解析
    ├── bsp_at_test.c/h      AT 指令逐条验证器
    ├── bsp_hex_test.c/h     HEX 交互协议逐报文验证器
    └── run.sh               一键编译运行脚本
```

## 快速上手

```bash
cd Code && ./run.sh                          # 编译+菜单（默认 /dev/ttyUSB0 @921600）
./imu_test /dev/ttyUSB0 921600 10            # 功能1：统计 10 秒
./imu_test /dev/ttyUSB0 921600 2 1           # 功能2：AT 验证（含风险组，自动还原）
./imu_test /dev/ttyUSB0 921600 3 2           # 功能3：HEX 压力/暴力模式
```

> 《用户协议》全量文档（AT 指令表、3.2 章串口交互协议）存于源工程 `01.Doc/用户协议.md`，本目录文档只摘录测试程序涉及的关键帧格式与判定规则。

## 沉淀经验（详见各模块文档）

1. **混流容错**：数据流推送帧与 AT 应答/HEX 应答同串口共存且可能字节级交织——先按帧结构整帧剔除 `AA 55` 推送帧，再做文本/帧判定（02/05/06）
2. **无锁 SPSC 队列**：单生产者/单消费者各持一个下标，volatile 即可安全解耦收发节奏（03）
3. **全样本 Δt 统计**：设备时间戳差值不做异常过滤，回退/重置直接体现在极值（04）
4. **副作用安全**：风险组用例一律"先查原值→设避让档→自动还原"，无法还原的项有意排除（05/06）
5. **固件即权威**：文档缺失/不一致处逐 ID 对照固件 `bsp_parse.c` 核实（0x0022 应答长度、SN 倒序等）（06）
6. **串口抢占陷阱**：两实例同读一串口会瓜分字节流，双方都无法组帧——排障先查 `lsof`（07）
