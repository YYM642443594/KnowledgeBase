# 3D姿态仪HUD交互优化报告

> 日期：2026-11-09 ｜ 项目：QT-Tools/CommTools ｜ 页面：3D模型+姿态仪合并页

## 背景

姿态仪以可拖动、可滚轮缩放的 HUD 小窗形式嵌入 3D 模型页（右下角初始 45% 页宽，位置/尺寸 Settings 持久化）。落地过程中踩了一系列 QML 交互与几何布局的坑，本文记录现象、根因与修法。

## 坑1：手写拖拽必须用父容器坐标系

- **现象**：姿态仪只能拖到中途就"卡住"，推不到窗口边缘（左/右/下方向明显，顶部因距离短不明显）。
- **根因**：QML `MouseArea` 的 `mouse.x/y` 是**相对 MouseArea 自身**的坐标。被拖动的小窗跟着鼠标一起动，鼠标的相对坐标几乎不变——直接用 `mouse.x - 按下点` 累加位移会互相抵消。
- **修法**：按下时 `mapToItem(parent)` 把鼠标映射到**父容器坐标系**记录锚点偏移；拖动时同样映射后 `位置 = 鼠标父坐标 − 锚点偏移`，再显式钳制 `[0, parent.width − width]`。**不要用内置 `drag.target`**——其边界在布局重算下会缩水导致单侧贴不了边。
- **附带**：钳制逻辑本身一直是好的；诊断方法是界面临时浮层输出 `pos/max/hud/page` 数值让用户报数，一次定位。

## 坑2：命令式赋值打断 QML 绑定 → 内容被裁切成"贴不了边"

- **现象**：HUD 拖到页面底边、钳制值 `y = maxY` 完全正确，但用户看到圆盘离边框很远。
- **根因**：HUD 高度本应绑定公式自适应内容（圆盘+读数面板+按钮），但三处命令式赋值打断了绑定：
  1. `Component.onCompleted` 恢复持久化时 `height = hudSize`（存的是旧正方形值）
  2. 窗口缩放跟随里 `height = newSize`
  3. 滚轮缩放里 `height = height * ratio`
  绑定断死后容器高 < 内容高，超出部分被裁切——视觉上就是"圆盘推不到边"，放大/缩小路径不同、症状不同，极具迷惑性。
- **修法**：**height 只由绑定公式管理，所有代码路径只赋值 width**；恢复持久化只恢复 x/y/width。诊断手段：界面浮层显示 `hud 宽x高`，高度<宽度即绑定已死。

## 坑3：组件内部留白让"贴边"看起来失败

- **现象**：拖拽与钳制都对，圆盘仍离边框 ~84px。
- **根因**：HUD 容器是正方形（`height = width`），圆盘直径公式 `min(width−40, height−180)` 在正方形下取 `width−168`，左右各 ~84px 不可见空白；顶部留白仅 16px 所以只有顶部"能贴边"。
- **修法**：① 容器高度改内容自适应公式；② 圆盘直径改**宽度驱动** `width − 8`（左右仅 4px 呼吸缝），删掉高度约束项。教训：**布局约束要单一驱动轴**，`min(宽, 高)` 双约束在容器比例变化时会产生不对称空白。

## 坑4：3D 轴标签投影——text 漏写 + 首帧 NaN 永久隐藏

- **现象1**：`View3D.mapFrom3DScene` 投影系统全程工作，但屏幕上看不到 XYZ。
- **根因1**：Repeater delegate 里 `text` 属性根本没写——坐标算出来了，Text 永远空白。
- **现象2**：补上 text 后仍时有时无。
- **根因2**：标签位置绑定是被动触发（相机属性变化才重投影）；首帧场景未就绪时 `mapFrom3DScene` 返回 NaN，`visible` 判定把它永久隐藏，直到用户手动转动相机。
- **修法**：① 补 `text: modelData`；② 加 150ms `Timer` 周期性递增 trigger 计数器强制重投影 + `Connections` 在相机 yaw/pitch/distance 变化时立即触发。经验：**依赖首次投影结果的绑定必须配定时兜底**，渲染器就绪时机不可依赖。

## 坑5：3D 模型旋转延迟——ViewModel 节流率低于渲染帧率

- **现象**：转动板子，姿态仪实时、3D 模型滞后一拍。
- **根因**：`Model3DViewModel` 用 50ms QTimer（20fps）节流 `rotationChanged` 发射；姿态仪拿即时数据，3D 走节流通道。
- **修法**：节流间隔 50ms → 16ms（60fps），与 QSG 渲染帧率对齐。经验：**同一数据源驱动多个视图时，节流率取最快视图的帧率**，否则各视图天然不同步。

## 坑6：读数面板缩放系数绑错基准

- **现象**：滚轮缩放 HUD 时圆盘变了，读数/按钮字号不变。
- **根因**：系数绑定用了 `root.width`（组件根宽，非内容驱动，不随内容重排变化）。
- **修法**：全部改绑 `attitudeBall.width`（圆盘真实直径）。经验：**等比缩放的基准必须是实际驱动内容尺寸的属性**，绑错基准表现为"部分元素不缩放"。

## 诊断方法论

GUI 程序 QML `console.log` 在 Windows 走 `OutputDebugString`，stdout/stderr 重定向捕获不到。最可靠的现场诊断是**界面临时浮层**（`Text { z: 999 }`）显示关键数值，让操作者报数；定位完成后立即移除。本次靠 `pos/max/hud/page` 四组数字一次区分了"钳制边界错"与"内容被裁切"两种此前混淆的症状。

## 涉及文件

- `Code/CommTools/View/MainView.qml` — HUD 容器、拖拽/缩放/钳制、持久化
- `Code/CommTools/View/Component/AttitudeIndicatorView.qml` — 圆盘宽度驱动、留白收紧
- `Code/CommTools/View/Component/Model3DView.qml` — XYZ 投影标签
- `Code/CommTools/ViewModel/Model3DViewModel.cpp` — 16ms 发射节流

对应提交：QT-Tools `477e3be`、QT_BSP `44072f8`（develop）。
