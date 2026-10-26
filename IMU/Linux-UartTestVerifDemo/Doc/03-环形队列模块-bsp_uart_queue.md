# 03 环形队列模块 bsp_uart_queue

> 源码：[Code/bsp_uart_queue.c](../Code/bsp_uart_queue.c) / [Code/bsp_uart_queue.h](../Code/bsp_uart_queue.h)

## 定位

串口字节流环形队列，衔接"接收线程（生产者）"与"解析线程（消费者）"，解耦两者节奏：串口突发到达时解析线程来不及消费的字节先在队列里缓冲。

## 数据结构

```c
#define UART_QUEUE_SIZE 4096   /* 容量(字节, 必须为2的幂): 921600bps下约42ms突发余量 */

typedef struct {
    unsigned char Buf[UART_QUEUE_SIZE];
    volatile unsigned int Head;       /* 写下标(仅生产者改) */
    volatile unsigned int Tail;       /* 读下标(仅消费者改) */
    volatile unsigned int DropCount;  /* 满时丢弃字节数 */
} UartQueue_S;
```

## 无锁 SPSC 原理

单生产者/单消费者（Single-Producer/Single-Consumer）场景下不需要锁：

| 变量 | 谁写 | 谁读 |
|------|------|------|
| Head | 仅生产者 push 后 `Head=(Head+1)&(SIZE-1)` | 仅消费者（判空/判满） |
| Tail | 仅消费者 pop 后 `Tail=(Tail+1)&(SIZE-1)` | 仅生产者（判满） |

- 每个下标只有一个写者 → 单字节写天然原子，`volatile` 足够，无需内存屏障（x86/ARM 单字读写保证）
- 容量取 2 的幂 → 取模运算退化为按位与，push/pop 均为 O(1)
- **判满用"放弃一格"法**：`(Head+1)%SIZE == Tail` 视为满，牺牲 1 字节容量换无锁实现

## 满时策略：丢新数据 + 计数

```c
void BspUartQueuePush(UartQueue_S *pQ, unsigned char Byte)
{
    unsigned int Next = (pQ->Head + 1) % UART_QUEUE_SIZE;
    if (Next == pQ->Tail) { pQ->DropCount++; return; }  /* 满则丢弃并累加 */
    pQ->Buf[pQ->Head] = Byte;
    pQ->Head = Next;
}
```

选择"丢新保旧"而非"丢旧保新"：丢字节必然破坏帧结构，被破坏的帧会被 CRC 拦下，`DropCount` 就是消费不及的直接证据——**正常情况必须为 0**，>0 即解析线程消费不及或突发过大，属于需排查的异常信号（与固件侧"ISR 队列满丢新字节"纪律一致）。

## 对外接口

| 函数 | 说明 |
|------|------|
| `BspUartQueueInit` | 清零三下标 |
| `BspUartQueuePush` | 生产者调用：入队 1 字节，满则丢+计数 |
| `BspUartQueuePop` | 消费者调用：出队 1 字节，空返回 -1 |

## 容量依据

921600bps ≈ 92.16KB/s，4KB ≈ **42ms 突发余量**。解析线程每秒只需消费 ~9 万字节（微秒级/字节），余量充足；若未来提速到更高波特率或解析变慢，按"波特率 × 期望容忍突发时长"重估容量并保持 2 的幂。
