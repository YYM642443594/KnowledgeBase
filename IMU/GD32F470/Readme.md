---
title: GD32F470 平台知识库
created: 2026-11-23
updated: 2026-11-23
tags: [IMU, GD32F470, 索引]
source: 原创
---

# GD32F470 平台知识库

> 2026-11-23 新建：GD32F470ZGT6 平台（1MB Flash / 25MHz 晶振 / 200MHz 主频）并入知识库。
> 固件工程 GD32F4xxMCU（BSP_501_PROJECT / HARDWARE_501_D00）+ 配套 GD32F4xx_Loader（升级框架
> bsp_loader 子仓库）。串口升级三通道 USART0/1/2（921600），分区设计与跳转失败修复见文档索引。

## 固件工程与产品映射

| 工程 | 仓库/分支 | 芯片 | 说明 |
|------|-----------|------|------|
| GD32F4xxMCU（APP） | GD32F4xxMCU.git，分支 `feature/IMUProject` | GD32F470ZGT6 | APP 链接基址 0x0800C000，BSP_501_PROJECT |
| GD32F4xx_Loader（Loader） | GD32F4xx_Loader.git，分支 `feature/upgrade`（内嵌 bsp_loader 子仓库） | GD32F470ZGT6 | Loader 0x08000000，升级框架多平台共用 |

## Flash 分区速查（GD32F470ZGT6, 1MB）

| 地址 | 区域 |
|------|------|
| 0x08000000 | Loader 代码（扇区0，实测 12KB） |
| 0x08004000 | APP 存在标志位（扇区1，独立扇区） |
| 0x08008000 | Loader 参数区 FlashInf_S（扇区2，独立扇区） |
| 0x0800C000~0x0801FFFF | APP 固件区 80KB（扇区3~4，升级擦除上界） |
| 0x08020000 / 0x08040000 | APP 参数页 A/B（扇区5/6，升级擦除不波及） |
| 0x08060000~0x080FFFFF | 预留（扇区7~11） |

## 文档索引

| 文档 | 主题 |
|------|------|
| [GD32F470串口Bootloader非均匀扇区分区设计与跳转失败修复报告](GD32F470串口Bootloader非均匀扇区分区设计与跳转失败修复报告.md) | 占位配置落入 1KB 页规划致擦参数毁 APP 向量表、非均匀扇区元数据独立扇区设计、APP_END 上界与固件总长校验、APP 三处地址同步、烧录恢复纪律 |
