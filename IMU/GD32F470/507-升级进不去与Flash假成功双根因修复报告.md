---
title: 507 升级进不去与 Flash 假成功双根因修复报告
created: 2026-11-23
updated: 2026-11-23
tags: [IMU, GD32F470, 507, 固件升级, FMC, FlashInf, 假成功]
source: 原创
---

# 507 升级进不去与 Flash 假成功双根因修复报告

> 现象：APP 收 0604 回 ACK 后复位，设备不进升级模式——loader 只短暂停留 2s 窗口即跳回 APP，
> 上位机来不及连接。深挖后发现两处独立根因叠加：**进升级机制语义用错**（清 APP 存在标志 vs
> 置 AppToLoaderFlag）+ **FMC 未解锁导致全部 Flash 写/擦假成功**。
> 本文纠正前篇《507-APP工程接入与指令参数存储升级链路报告》中"0604 清标志进升级"的旧机制描述。

## 1. 根因一：进升级机制语义错误（清 APP 存在标志 ≠ 进升级）

**Loader（GD32F4xx_Loader app_upgrade.c，三平台共用）上电判断真实逻辑**：

```
AppUpgradeBootProcess()
  ├─ AppUpgradeIsWaitUpgrade(): FlashInf.AppToLoaderFlag == 0x01 ?
  │     └─ 是 → 常驻待升级模式（断电重启也不跳APP） ← 这才是"升级模式"
  ├─ BootCount >= 3 ? → 同样常驻待升级
  └─ APP存在标志(0x08004000) == 0x5A5A5A5A ?
        ├─ 是 → 开2s等待窗口 → 超时跳APP
        └─ 否 → AppUpgradeAppValidate()校验固件区有有效APP
              └─ 是 → 补写标志 + 开2s窗口 → 超时跳APP   ← 清标志走的是这条路
```

**清 APP 存在标志（0x08004000）进不了升级，且有两重危害**：

1. 标志无效时 loader 只是"校验固件区→补写标志→2s 窗口→超时跳回 APP"——设备根本不停留；
2. 即使进入升级且完成，loader 周期任务按"APP 标志有效"才跳新固件——标志被清了会
   **拒绝跳转，卡死在 loader**。

**正确机制**：0604 → 置 **loader 参数区（0x08008000, sector2）AppToLoaderFlag = 0x01** →
复位 → loader 常驻待升级 → 升级完成 loader 置回 0xFF + 按 APP 标志自动跳新固件。
（GD32F1xx 工程同款实现已量产验证，507 直接镜像。）

## 2. 根因二：FMC 未解锁 → 全部 Flash 写/擦"假成功"

**现象级坑**：GD32F4 的 `FMC_CTL` 在 `LK=1`（上电默认锁定）时**写保护**——
`fmc_sector_erase / fmc_word_program` 内部对 CTL 置 SER/START/PG 位全部无效，
擦除/编程**什么都没发生，但库函数照常返回 FMC_READY**（假成功）。无报错、无异常，
表象只能是"写进去的数据读不回来/没生效"。

**本工程层次设计**（与 loader 侧不同）：

- 主工程 `hal_flash.c`：`HalFlashUnlock/HalFlashLock` 独立接口，设计约定"**调用方负责**
  写/擦前解锁、完成后上锁"（hal_flash.h 注释明示）；
- loader 仓库 `hal_flash.c`：写函数**内部自带 unlock/lock**（自包含）。

**事故**：主工程 `drv_flash.c` 三个写/擦入口（DrvFlashWrite32BitData /
DrvFlashWordProgramNoErase / DrvFlashSectorErase）**全都没有调用 Unlock/Lock**，
全仓库零调用 → APP 侧所有 Flash 操作假成功：

| 受害功能 | 表象 |
|---|---|
| 升级标志清零（0604 链路） | 标志写不进，叠加根因一彻底进不了升级 |
| **参数页 A/B 写入（参数存储功能）** | 参数从未真正落盘——此前提交的功能实际无效，未被实测暴露 |

**修复**：drv_flash.c 三入口统一补 `HalFlashUnlock()` / `HalFlashLock()`（本工程唯一解锁点，
保持 Hal 层"调用方负责"约定；DrvFlashWordProgramNoErase 修复后因机制纠正不再被 0604 使用，
保留为通用纯字编程接口）。

## 3. Loader 参数区 FlashInf_S 布局（24 字节，三方对齐）

| 偏移 | 字段 | 说明 |
|---|---|---|
| 0 | Magic (1B) | 有效值 0x5A（FLASH_INF_MAGIC），无效时 loader 上电整区重置 |
| 4 | LoaderVersion (4B) | loader 版本，升级完成时刷新 |
| 8 | UpgradeDate (4B) | 升级日期，升级完成时刷新 |
| 12 | **AppToLoaderFlag (1B)** | **0x01=待升级常驻；0xFF=正常** |
| 16 | BootCount (4B) | 连续启动失败计数，≥3 也判待升级；升级完成清零 |
| 20 | CRC8 (1B) | **覆盖偏移 0~19 字节（含 Flag）**，初值 0x77 查表法 |

关键约束：AppToLoaderFlag 受 CRC8 保护——**单字节改写**会使 loader 上电校验失败而
整区重置（标志丢失），必须"读出→修改→重算 CRC→擦 sector2→整区 24B 写回"。
CRC8 算法与 BSP_IMU `BspCRC8ValueCal`（bsp_crc.c）完全同款（同一协议库），
drv 层直接 include 复用，零重复代码。

## 4. 修复实现（drv_chip_common.c DrvUpgradeChipRest）

```c
DrvFlashRead32BitData(0x08008000, 24, Word);        /* 读原24B(版本/日期/BootCount保持) */
/* Word→buf 字节视图(独立数组,规避对齐/别名问题) */
if (buf[0] != 0x5A) { memset(buf,0,24); buf[0] = 0x5A; }  /* 未初始化兜底 */
buf[12] = 0x01;                                      /* AppToLoaderFlag = 待升级 */
buf[20] = BspCRC8ValueCal(buf, 20);                  /* 重算CRC8 */
/* buf→Word 小端重组 → 擦sector2 → 整区写回 */
delay_1ms(2000);                                     /* 0604的ACK已回,留收尾时间 */
NVIC_SystemReset();
```

配套改动：bsp_drv.h 507 段宏 `UPGRADE_SYMBOL_FLAG_ADDR(0x08004000)` 废弃，
改 `IMU_507_LOADER_PARAM_ADDR 0x08008000`（对齐 506 段宏模式；APP 存在标志
全程由 loader 维护，APP 不读写）。

**修复后全链路闭环**：0604 → ACK+参数落盘 → 置 Flag → 复位 → loader 常驻待升级 →
上位机从容连接发固件（921600，三通道）→ 完成后 loader 置回 Flag + 刷版本日期 +
按 APP 标志跳新固件。

## 5. 升级交付物：编译产出 bin

- build_ac5.ps1：链接成功后 `fromelf --bin` 生成 `build_ac5\GD32F450.bin`
  （从 IROM1 起始 0x0800C000 的纯二进制镜像，loader 0604 链路直接烧写用）；
- Project.uvprojx：AfterMake 启用同款 fromelf 命令（IDE 编译同步产出）——
  **修正了原配置引用 Project.axf 与实际输出名 GD32F450.axf 不符、bin 从未生成过的问题**；
- 验证：bin 首 8 字节 `00 23 00 20 C5 C1 00 08` = 栈顶 0x20002300 + 复位向量 0x0800C1C5，
  与 HEX 首数据行一致；40184B ≈ 39.2KB（ROM<80KB 约束内余量充足）。

## 6. 教训

1. **跨仓库接口（APP↔loader）必须对读对方判断代码**，不能凭文档、旧平台记忆或
   "参照 303 清标志"的口口相传——本次机制错误正是照搬了 303 旧平台语义（而 loader
   三平台实际共用新 FlashInf 机制）。F1 工程有现成正确实现，**优先找参照工程**。
2. **警惕"假成功"类 API**：GD32F4 Flash 库函数在 FMC 锁定态照常返回 READY。
   修复后参数存储/升级标志才真正生效——此前功能提交过但"没实测出问题"不等于正确。
3. **hal/drv 分层解锁约定要闭环验证**：设计注释写了"调用方负责解锁"，但没有
   排查调用方是否真的调用（全仓库 grep Unlock 调用点为零即暴露）。
4. **IDE 打开的文件缓冲会回写覆盖外部修改**：本次 bsp_drv.h 修改曾被 IDE 旧缓冲
   保存覆盖（编译通过但文件回退），提交前务必 `git diff` 复核文件真实状态。
