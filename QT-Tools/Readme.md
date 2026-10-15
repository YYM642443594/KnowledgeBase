# QT-Tools / CommTools 上位机

志翔 IMU 上位机（Qt 6 / QML），串口调试 + Hex 指令 + 3D 姿态 + 固件升级一体工具。

## 仓库与渠道

| 项 | 值 |
|----|----|
| 工程主仓 | `https://gitee.com/YYM642443594/QT-Tools.git`（develop 分支） |
| bsp 子模块 | `https://gitee.com/YYM642443594/QT_BSP.git`（Code/CommTools/bsp） |
| 本机路径 | `F:\00.Code\09QT\QT-Tools`（2026-10-10 20 时起；历史位置 `E:\00.YYM\06.Code\QT-Tools` 已迁） |
| gitee 操作 | 每条命令带 `-c http.proxy= -c https.proxy=` 绕过死代理 |
| GitHub 知识库 | 本仓库（KnowledgeBase），SSH 推送 `git@github.com:YYM642443594/KnowledgeBase.git` |

## 本机构建（Qt 6.11.1 MSVC + jom，2026-10-10 20:00 验证通过）

> 工程现位于 `F:\00.Code\09QT\QT-Tools`，Qt Creator 配置为
> `build\Desktop_Qt_6_11_1_MSVC2022_64bit-Debug`（NMake Makefiles JOM）。
> 根目录 build.bat 引用的 `E:\QT_Tools\...` 与 `C:\Qt\6.10.2\msvc2022_64` 均已不存在，勿直接使用。

```powershell
# 增量构建（首次全量约几分钟）
ps> cmd.exe /s /c '"D:\software\25VisualStudio\product\VC\Auxiliary\Build\vcvars64.bat" && cd /d F:\00.Code\09QT\QT-Tools\Code\CommTools\build\Desktop_Qt_6_11_1_MSVC2022_64bit-Debug && D:\software\22.QT\Tools\QtCreator\bin\jom\jom.exe"'
# 链接失败 LNK1168 = CommTools.exe 在运行，先 taskkill /F /IM CommTools.exe
# 自测（构建目录未部署 Qt DLL，需前置 Qt bin；否则 0xC0000135 秒退）
ps> $env:Path = "D:\software\22.QT\6.11.1\msvc2022_64\bin;" + $env:Path
ps> & "F:\00.Code\09QT\QT-Tools\Code\CommTools\build\Desktop_Qt_6_11_1_MSVC2022_64bit-Debug\CommTools.exe" --simulate --seconds 8 --size 1600x900 --grab out.png
```

旧 MinGW 6.9.3 方案（E: 路径时期，历史保留）：Qt 仅 mingw_64 kit 于 D:\Qt\6.9.3，
CMake -G Ninja -B build\cli-Debug，全量 70 步约 1 分钟。

## 源码结构（与本知识相关部分）

- `Code/CommTools/ViewModel/CommandViewModel.cpp` — Hex 指令注册（initCommandGroups）/ 发送构建（buildPayload）/ 回复解析（handleReceivedData）
- `Code/CommTools/bsp/Help/DataParser.h` — 协议结构体（Hex*_S 系列，`#pragma pack(1)`）
- `Code/CommTools/bsp/Common/crc.cpp` — CRC16：init=0x3692、poly=0x8408（LSB-first）
- `Code/CommTools/View/Component/DebugPage.qml` — XCOM 风格调试页
- `Doc/协议规范/IMU-用户协议.md` — 协议唯一事实来源；`指令解析方案.md` — 开发规范

## 记录索引

- 2026-10-10 [HexCommands 实现核对与修复报告](Doc/HexCommands-实现核对与修复报告.md) — 17 条指令全量核对、5 处修复、COM8 实测证据
- 2026-10-10 [XCOM 功能对照报告](Doc/XCOM功能对照报告.md) — DebugPage vs ATK-XCOM
- 2026-10-10 [波形页优化报告](Doc/波形页优化报告.md) — 卡顿三根因、Y轴自适应、鼠标缩放/平移查看（X轴§11 / Y轴§13）、**滚轮无效根因§14（qmlcachegen 编译下 MouseArea.onWheel 失效，改用 WheelHandler）**、数据入口过滤根因(§12)、自测钩子与实测数据
- 2026-10-10 [蓝牙功能实现](Doc/蓝牙功能实现.md) — Windows 原生双栈(WinRT AEP 扫描+Winsock SPP 免配对直连，Qt Bluetooth 缺失且 Windows 不支持经典 SPP)、cppwinrt 踩坑(/permissive-/experimental-coroutine/runtimeobject)、--btscan 实测 20s 扫到 12 台
- 2026-10-15 [页面切换卡顿优化报告](Doc/页面切换卡顿优化报告.md) — 两轮共 5 批次：P0（QList<double>/seq 增量日志/perfLog 门控/RelWithDebInfo）+ P1/P2（页面 3-6 Loader 延迟加载、波形 C++ 侧供数 fillChart 彻底消灭数组转换与 Qt.point 分配、--serial/--cyclepages 自测钩子）；COM3@921600 真实设备全链路验证（注意设备波特率 921600）；B5（QML_ELEMENT AOT）因 Qt6.11+MSVC 命名空间元对象链接 C2737 回退，重试路径见报告
- 2026-10-15 [页面切换卡顿优化报告](Doc/页面切换卡顿优化报告.md) — P0 三连修：①13 通道波形属性 QVariantList→QList<double>（消除每 tick 16 绑定×1500 点 QVariant 装箱转换）②调试页日志改后端 seq 增量拉取 rxLogsSince/lastLogSeq（替代每次全量拷贝 5000 条）③perfLog 默认关闭（COMMTOOLS_PERF_LOG 开启）；新增 RelWithDebInfo 构建目录（jom 须 -DCMAKE_MAKE_PROGRAM 全路径）；--simulate 像素计数 + --btscan 日志链路 0 错误验证
- 2026-10-10 [协议开发规范](Doc/协议开发规范.md)（项目内 `指令解析方案.md` 修复后快照）
