# HEXCommands 协议全量审计与 3D 轴标签重构报告（2026-11-10）

工程仓提交：QT-Tools develop `a3f794a`（gitee）。本报告整理两项工作：HEXCommands 页与协议文档的全量对照审计，以及 3D 页 XYZ 轴尖标签从 2D 投影到场景内广告牌的重构。

## 一、HEXCommands 协议审计（对照 IMU-用户协议.md 3.2.3/3.2.4）

### 审计方法

- 逐条列出协议文档串口交互协议全部命令（0x00 组 20 条 + 0x01 组 3 条），与 `CommandViewModel::initCommandGroups()` 命令表、`buildPayload()` 载荷构造、字段定义表三方对照。
- 全库搜索缺失命令码（`0x21|YAW.*归零`），排除 CRC 表误命中后确认零实现。

### 审计结果

| 协议命令 | 结论 |
|---|---|
| 0x00 0x01/0x02/0x09/0x10/0x13 推送数据查询 | 一致（查询型，仅命令头） |
| 0x00 0x03 版本查询 | 一致 |
| 0x00 0x04 频率设置/查询 | 一致（op 支持 RAM/FLASH） |
| 0x00 0x05 蓝牙名称（16 字符串） | 一致 |
| 0x00 0x06/0x07/0x08 单字节控制值 | 一致 |
| 0x00 0x11 推送报文 ID 控制（CMD+ID+开关 3 字节） | 一致 |
| 0x00 0x12 PPS 开关+模式（2 字节） | 一致 |
| 0x00 0x14 复位重启 / 0x18 SN 查询 / 0x20 零偏校准 | 一致（DATA1+Reserved8 帧型） |
| 0x00 0x15 坐标系（2 字节小端） | 一致 |
| 0x00 0x16/0x17 波特率（4 字节 32 位，如 0x80250000=9600） | 一致 |
| 0x00 0x19 时间设置（年2LE+月日时分秒+Reserved8，3 种输入格式兼容） | 一致 |
| **0x00 0x21 YAW 角归零重置** | **缺失 → 已补齐** |
| 0x01 0x01 A 值 / 0x02 全量推送 / 0x03 电池电量 | 一致 |

### 0x21 补齐（三处，CommandViewModel.cpp）

1. 命令表 group0 追加 `id 21 / subId 0x21 / "YAW角归零重置"`；
2. `buildPayload()` `case 0x21` 并入 0x14/0x18/0x20 帧型（DATA 1 字节 + Reserved 8，协议 3.2.3.15）；
3. 字段定义表同帧型提示 data1 控制值（0x01 重置）。

### 验证

- CRC16 自检对齐文档示例 `AA 55 01 01 00 0A 00 00 → CA B0` ✓；
- 0x21 帧构造离线验证：`AA 55 00 21 01 12 00 01 00…00 9A 16`，v_len=7+9+2=18=0x12 ✓；
- 构建通过、HexCommands 页 0 QML 错误；
- 真机收发未做（审计时无串口设备）——设备接入后补一次实机确认。

> 范围说明：CAN 协议（3.3）不在 HEXCommands 页范围。CAN `0x112` 同为 YAW 归零，后续若做 CAN 页需同步覆盖。

## 二、3D 轴尖 XYZ 标签重构：2D 投影 → 场景内广告牌

### 根因（逐层实证）

上一提交（477e3be）的 labelLayer 用 `view.mapFrom3DScene()` 把 3D 轴尖投影到 View3D 外的 2D 覆盖层。本会话逐层二分（强制 visible、magenta/cyan/yellow 探针方块、纯色无纹理方块）证明：**mapFrom3DScene 在本场景持续返回 NaN/无效坐标**，投影方案本身不可用；历史"自测通过"记录实际未真正生效。

### 新方案：场景内广告牌

- 轴尖 (±220,0,0)/(0,±220,0)/(0,0,±220) 放置 `#Rectangle` 面板 Model，贴 Canvas 绘制的字母纹理（AxisLetter inline component，64px canvas、无粗体 sans-serif）；
- `eulerRotation.y = cameraYawAngle + 180`、`eulerRotation.x = -cameraPitchAngle` 反向绑定相机 rig 角度，面板始终面向屏幕；
- 材质 `NoLighting + emissive(1,1,1) + Blend + NoCulling`，任何视角原色可见；
- **必须置于 View3D 场景内**（axisHelper 旁）——第一版放 View3D 外，纯色探针 0 像素暴露了层级错误。

### 排坑记录（复用价值高）

1. **inline component 名称全文件唯一**——旧块残留的重复 `component AxisBillboard` 导致 qmlcachegen 编译失败 `Inline component names must be unique per file`；删块要删干净（含实例和辅助 Node）。
2. **Texture.sourceItem 的 parent 链陷阱**——Texture 非 Item，`parent.parent.xxx` 引用无效导致纹理黑屏；改用 `property alias srcCanvas: texMapper.sourceItem` + 实例处显式绑定。
3. **实例化 inline component 的语法**——`Canvas { letter: "X"; AxisLetter {} }` 会把属性设到外层 Canvas 上报 `Cannot assign to non-existent property "letterColor"`；必须直接 `AxisLetter { letter: "X" }`。
4. **PowerShell 改源码必炸**——`Set-Content -Encoding UTF8` 写入 BOM 且破坏中文注释行结构（QML 语法错、括号平衡 depth=-5）；改 E:\ 源码一律走 Python `[IO.File]`-equivalent（`io.open` utf-8 surrogateescape + newline=''），损坏后从 .bak 恢复重打补丁。
5. **验证手段**——`--page 3/4 --seconds 8 --grab` 截图 + Python PIL 按标签色精确聚类 + ASCII 像素图形状确认（X/Z 字母形状清晰可辨）；QML 错误看 `debug.log`（注意区分新旧时间戳的历史错误）。

### 验证结果

- X 字母（红 #ef4444）：默认视角 ASCII 像素图呈现清晰 X 形；
- Z 字母（蓝 #3b82f6）：yaw=40° 测试视角下清晰 Z 形（上下横杠+斜线），验证后默认视角已还原 0；
- Y 在默认视角被自身轴线遮挡（广告牌法向与视线夹角），旋转视角即正常显示，与真实 3D 行为一致。

## 同步更新

- 知识库 Readme.md 索引追加本报告。
