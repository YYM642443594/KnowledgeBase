# 02 串口驱动模块 drv_serial

> 源码：[Code/drv_serial.c](../Code/drv_serial.c) / [Code/drv_serial.h](../Code/drv_serial.h)

## 定位

Linux termios 串口驱动层，**仅封装系统调用，不含任何协议逻辑**。更换平台（如 Windows/RTOS）时仅需重写本层，上层不变。

## 对外接口

```c
typedef struct {
    int  Fd;        /* 文件描述符, -1=未打开 */
    char Dev[64];   /* 设备路径, 如 /dev/ttyUSB0 */
    int  Baud;      /* 波特率数值, 如 921600 */
} DrvSerial_S;

int  DrvSerialOpen(DrvSerial_S *pDrv);                        /* 打开并配置(Dev/Baud先填好) */
void DrvSerialClose(DrvSerial_S *pDrv);
int  DrvSerialRecv(DrvSerial_S *pDrv, unsigned char *pBuf, int Len);  /* 阻塞收, >=1字节即返回 */
int  DrvSerialSend(DrvSerial_S *pDrv, const unsigned char *pBuf, int Len); /* 循环写直到发完 */
```

## Open 配置要点（实现逐条）

| 配置 | 做法 | 目的 |
|------|------|------|
| 打开方式 | `open(Dev, O_RDWR \| O_NOCTTY \| O_SYNC)` | 不作为控制终端，避免串口上的杂散输入影响进程 |
| 波特率 | 数值→宏映射表（9600~921600 八档），`cfsetispeed/cfsetospeed` | 协议默认 921600，非法波特率直接报错拒开 |
| 帧格式 | 8 数据位 / 无校验 / 1 停止位，无流控（`~CRTSCTS`、`~IXON/IXOFF/IXANY`） | 协议默认 8N1 |
| 原始模式 | 清 `ICANON/ECHO/ECHOE/ISIG`、`OPOST`、`INLCR/ICRNL` | 二进制协议透传，不做任何字符处理 |
| 读阻塞 | `VMIN=1, VTIME=0`：收到 ≥1 字节即返回 | 半阻塞读，上层大缓冲读满整包 |
| 清残留 | `tcflush(TCIOFLUSH)` 后再 `tcsetattr` | 丢弃历史残留字节，验证从干净状态开始 |
| USB 低延迟 | `TIOCGSERIAL/TIOCSSERIAL` 置 `ASYNC_LOW_LATENCY` | CH340/CP210x 等 USB 转串口默认 1 个 UART FIFO 延迟（约几十 ms 级），置位后降到 1ms 级 |

## 收发实现细节

- **Recv**：`read()` 返回 `<0` 且 `errno==EINTR` 时自旋重试——信号（Ctrl+C）只打断一次 read，不丢运行控制；返回 0 = 对端断开（如 USB 拔出），返回负 = 错误
- **Send**：循环 `write()` 直到全部发出，`EINTR` 重试，其余错误直接失败返回——保证任意长度指令帧完整落串口

## 经验沉淀

1. **低延迟标志对 USB 串口必备**：验证帧间隔统计（1ms 级）时，未开 `ASYNC_LOW_LATENCY` 的 USB 转串口会把抖动放大到几十 ms，统计结果失真
2. **VMIN=1 而非纯阻塞**：配合信号驱动退出（sigaction 无 `SA_RESTART`），Ctrl+C 能即时打断读循环，避免"退不出"的假死
3. 原始模式下务必同时清输入标志（`INLCR/ICRNL`）与回显标志——否则 0x0A/0x0D 字节会被改写，二进制帧 CRC 必错
