---
title: 507 推送时间戳 DWT 实测 us 时基修复报告
created: 2026-11-23
updated: 2026-11-23
tags: [IMU, GD32F470, 507, 时间戳, DWT, SysTick]
source: 原创
---

# 507 推送时间戳 DWT 实测 us 时基修复报告

## 1. 现象

507 推送帧时间戳完全均匀：50Hz 推送相邻帧恒 `+20000`（us），如
120760000 → 120780000 → … → 122720000，98 帧无一抖动、无一重复。
"过于完美"反而是异常信号。

## 2. 根因：名义时间 vs 实测时间

- 507 算法链摘除后（无传感器 dt 累加），时间基采用**过渡方案**：主工程 SysTick 回调
  每拍固定 `BspSysRunTimeSet(1000)`——即"名义 1ms/拍"累加。
- 结果：G_SysRunTime 是纯名义时间（恒整毫秒平铺），推送帧时间戳虽有正确的时间流逝
  速度，但**粒度被钳在 1ms、且不携带任何真实时刻信息**。
- 对照 506 方式（bsp_function.c 注释明示）：运行时间戳由 **SysTick 中断（1ms 节拍）按
  注册的 us 时基源实测增量锁存**（bsp_run_ctrl.c `BspSysTickMs` → `G_UsTimeSource()`），
  残差仅剩中断响应延迟（±50us 内），保留 us 级分辨率。

## 3. 修复（3 文件，仅 507 分支）

1. **bsp_drv.c** 新增 507 平台段（GD32F470）：
   - `BspDrvUsTimeSourceGet`：DWT CYCCNT **32 位回绕安全差分**（`NowCycles - LastCycles`
     无符号溢出即回绕）→ `dwt_us_from_cycles32` 换算 us。增量契约与 351/303 段一致：
     仅 SysTick 中断（1ms）调用，1ms 远小于回绕周期永不漏圈；禁止其它位置调用
     （额外调用会"偷走"增量使时间戳变慢）。
   - `BspDrvUsTimeSourceInit`：预热一次建增量基准 + `BspSysUsTimeSourceRegister` 注册。
     **不得重复调用 DWT 初始化**——主工程 AppInit 已 `DrvDwtInit`（且 SysTick 回调经
     `DrvDwtDbgDetachReset` 维持，调试器掉线整机复位重跑），清零 CYCCNT 会使已建基准
     产生整周期级错误差分。
2. **app_main.c**：SysTick 回调删固定 `BspSysRunTimeSet(1000)`（改由 `BspSysTickMs` 内
   按注册源实测累加）；AppInit 在 `DrvDwtInit` 之后调 `BspDrvUsTimeSourceInit`；补
   include bsp_drv.h（漏原型 → AC5 隐式声明告警，警告基线 10→12 即此信号）。
3. **bsp_function.c**：507 同步注释（BspSystemTimeSync(BspSysRunTimeGet()) 保留不变）。

## 4. 陷阱与检查单

- **符号差异**：主仓库 dwt.h 冻结符号是 `dwt32_cycles`/`dwt_us_from_cycles32`/`DrvDwtInit`；
  bsp_drv.c 351/303 段用的 `dwt_cycles32`/`dwt_timer_init` 是旧平台符号，照抄会链接失败
  ——抄平台段前先核对目标平台 dwt.h 实际符号。
- **注册时序**：预热+注册须在 DWT 初始化后、且越近越好；注册前 SysTick 已跑的拍数
  （G_UsTimeSource==NULL 不累加）丢失属可接受（毫秒级）。
- **验证方法**：实机重测 50Hz 推送相邻时间戳应为 `≈20000 ± 中断延迟抖动（±50us）`的
  真实微秒值（如 20013、19987）；若仍恒 20000 → 时基源未生效（注册时序/预热遗漏）。

## 5. 提交

BSP_IMU `develop` @ `91f3f42`；主工程 `feature/IMUProject` @ `38a97fb`。编译 0 失败 /
10 警告=基线 / LINK OK / HEX 基址 0x0800C000。

## 关联文档

- [507-APP工程接入与指令参数存储升级链路报告](507-APP工程接入与指令参数存储升级链路报告.md)
