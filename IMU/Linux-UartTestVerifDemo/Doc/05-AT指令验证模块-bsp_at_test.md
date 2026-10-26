# 05 AT 指令验证模块 bsp_at_test

> 源码：[Code/bsp_at_test.c](../Code/bsp_at_test.c) / [Code/bsp_at_test.h](../Code/bsp_at_test.h)
> 依据：源工程《用户协议》第 2 章 AT 指令表

## 定位

AT 指令逐条自动验证器：用例表驱动，逐条下发 → 按文档应答格式判定 → 汇总表输出。入口 `BspAtTestRun(pDev, Baud, RunRisk)`，返回 0=全过 / 1=有失败 / -1=串口打开失败。当前共 **40 条用例**（模式 0 仅安全组 20 条；模式 1 加风险+异常 40 条）。

## 用例表结构

```c
typedef struct {
    char         Cmd[48];     /* 指令文本(可含%d占位, 运行时格式化) */
    AtCaseType_E Type;        /* QUERY查询 / ACTION动作 / SCALESET量程设置 / TIMESET时间设置 */
    AtGroup_E    Group;       /* SAFE安全组 / RISK风险组 */
    const char  *pName;       /* 中文名(汇总表显示) */
    const char  *pRestore;    /* 还原指令(NULL=无) */
    const char  *pExpect;     /* 期望应答关键字(逗号分隔) */
} AtCase_S;
```

## 分组与覆盖（V1.7.0）

| 组别 | 内容 | 判定 | 副作用处理 |
|------|------|------|-----------|
| 安全组 | 17 条只读查询（`VERSION?/BAUD?/SET?/CONFIG/COORDINATE?/PPS?/PPSMODE?/PUSHFRQ?/SN?/DATATIME?/DATALINK?/GRAPHRQ?/ORIGRQ?/CANBAUD?/FLASHCFG/ACCSCALECFG?/GYROSCALECFG?`）+ `SET=OFF/ON` 开关成对 + `YAWRESET` | 查询类按文档应答**逐关键字匹配**（如 `AppVersion:`、`HardwareVersion:`）且必须收到 `OK`；动作类收到 `OK` 即过 | SET 成对执行后恢复原态 |
| 风险组 | PPS 开关与模式、MSGID=13/22 推送开关、GRAPHRQ/ORIGRQ 频率、DATALINK 链路开关、ZEROBIASCAL 零偏校准、量程配置（SCALESET）、系统时间设置（TIMESET）、`AT+RST` 复位 | 同上 | **成对/自动还原**（见下） |
| 有意排除 | `BAUD=/COORDINATE=/PUSHFRQ=/CANBAUD=` | — | 掉电保存且断链/改数据语义，自动流程不碰，建议手动单项 |

## 副作用安全设计

1. **成对紧邻还原**：`AT+PPS=ON` → `AT+PPS=OFF`，验证即还原
2. **先查后设再还原**：
   - TIMESET：先 `AT+DATATIME?` 查原时间 → 设测试时间 → 还原原时间（掉电不保存）
   - SCALESET：先 `ACCSCALECFG?/GYROSCALECFG?` 查原量程 → 设避让档（原值 16g 则设 8g）→ 写回原值
3. **复位置表末**：`AT+RST` 固定最后执行（断流数秒不影响前面用例）
4. 还原动作不计分，失败清单单列

## 混流容错（核心难点）

设备数据流（50Hz 文本/二进制推送帧）与 AT 应答共存同一串口，且可能**字节级交织**（曾致真机假 FAIL：`AccScaleCf`+推送帧+`g:16` 关键字被打断、噪声假 `OK` 提前截断缓冲）。接收路径三步处理：

```text
AtPumpBytes(read收包) → AtFilterSliding(滑窗剔帧+转可见文本) → AtRecvResp(完整应答判定)
```

1. **剔推送帧**（`AtSkipPushFrame/AtTrySkipFrame`）：缓冲内滑窗找 `AA 55`，按帧结构（CMD/ID/LEN）整帧剔除，帧内可见字节不再污染应答文本
2. **过滤不可见字节**：剔除后剩余字节转可打印字符入应答缓冲（`AtAppendVis`）
3. **双条件完整判定**（`KeysAllBefore/KeyInBefore`）：要求**全部期望关键字齐备 + 其后有 `OK\r\n`** 才截断应答；假 `OK`（其前无关键字）自动跳过继续等真应答；超时 1200ms 时已有 OK 仍交上层按关键字判定
4. 原始应答片段原样打印（`pNote`/汇总表），便于人工复核

## 单条执行与输出

- 安静模式：每条指令一行（`发送过程不刷屏`），结束后输出对齐汇总表（序号/指令/结果 PASS/FAIL/提取值）+ 失败清单
- 提取值（`ExtractVals`）：按期望关键字从应答中提取对应值（如版本号、波特率数值）
- 名称列按 **UTF-8 显示宽度**补空格（中文按 2 列计），中英混排不错位

## 关键参数

| 常量 | 值 | 说明 |
|------|-----|------|
| `AT_RESP_TIMEOUT_MS` | 1200 | 单条应答超时（数据流混流留余量） |
| `AT_RESP_MAX` | 1024 | 过滤后应答缓冲 |
| `AT_CASE_MAX` | 64 | 用例上限 |

> pty 冒烟：模式 0 与模式 1（构造假 OK + 推送帧打断关键字交织场景）40/40 PASS。
