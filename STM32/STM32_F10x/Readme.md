# STM32_F10x

基于 STM32F10x 的嵌入式工程仓库，架构规范采用跨仓库通用模板 `Project_Level_Skill.md`（可直接复制到其他 MCU 工程复用）。

## 架构形态

- **运行时调用链（严格单向）**：`APP → DRV → HAL → 厂商官方库 → MCU`
- **BSP 为板级兼容层**（旁路支撑，不在调用链上）：
  - `bsp_config.h`（板级配置表）：引脚/串口号/器件地址/实例表，DRV/APP 唯一的板级参数来源
  - `bsp_board.c`（板级初始化）：上电时序/时钟/电源使能/引脚复用，经 HAL 实现
- **移植口径**：换 MCU 重写 HAL；换 PCB 只改 `bsp_config.h`（必要时调整 `bsp_board.c` 时序）
- 仓库形态支持两种：主仓库(HAL) + 子仓库(BSP/DRV/APP, 形态A 为 Submodule)；或单仓库内模块目录（形态B）

## 文档索引

| 文档 | 说明 |
|------|------|
| [Project_Level_Skill.md](./Project_Level_Skill.md) | 嵌入式项目架构规范（跨仓库通用模板） |
| [Doc/架构调整-四层改三层.md](./Doc/架构调整-四层改三层.md) | 分层架构由四层调整为三层（BSP 下沉为板级兼容层）的调整记录 |
