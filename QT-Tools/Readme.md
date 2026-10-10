# QT-Tools / CommTools 上位机

志翔 IMU 上位机（Qt 6 / QML），串口调试 + Hex 指令 + 3D 姿态 + 固件升级一体工具。

## 仓库与渠道

| 项 | 值 |
|----|----|
| 工程主仓 | `https://gitee.com/YYM642443594/QT-Tools.git`（develop 分支） |
| bsp 子模块 | `https://gitee.com/YYM642443594/QT_BSP.git`（Code/CommTools/bsp） |
| 本机路径 | `E:\00.YYM\06.Code\QT-Tools` |
| gitee 操作 | 每条命令带 `-c http.proxy= -c https.proxy=` 绕过死代理 |
| GitHub 知识库 | 本仓库（KnowledgeBase），SSH 推送 `git@github.com:YYM642443594/KnowledgeBase.git` |

## 本机构建（Qt 6.9.3 MinGW，2026-10-10 验证通过）

> 注意：本机 Qt 只有 **mingw_64** kit（D:\Qt\6.9.3\mingw_64），无 MSVC kit；
> 根目录 build.bat 引用的 `E:\QT_Tools\...` 与 `C:\Qt\6.10.2\msvc2022_64` 均已不存在，勿直接使用。

```powershell
$env:PATH = "D:\Qt\Tools\mingw1310_64\bin;D:\Qt\6.9.3\mingw_64\bin;D:\Qt\Tools\Ninja;D:\Qt\Tools\CMake_64\bin;" + $env:PATH
$src = 'E:\00.YYM\06.Code\QT-Tools\Code\CommTools'
& 'D:\Qt\Tools\CMake_64\bin\cmake.exe' -G Ninja -S $src -B "$src\build\cli-Debug" -DCMAKE_PREFIX_PATH='D:/Qt/6.9.3/mingw_64' -DCMAKE_BUILD_TYPE=Debug
& 'D:\Qt\Tools\CMake_64\bin\cmake.exe' --build "$src\build\cli-Debug"
```

全量 70 步约 1 分钟；产物 `build\cli-Debug\CommTools.exe`。运行前需 windeployqt 或保持 Qt bin 在 PATH。

## 源码结构（与本知识相关部分）

- `Code/CommTools/ViewModel/CommandViewModel.cpp` — Hex 指令注册（initCommandGroups）/ 发送构建（buildPayload）/ 回复解析（handleReceivedData）
- `Code/CommTools/bsp/Help/DataParser.h` — 协议结构体（Hex*_S 系列，`#pragma pack(1)`）
- `Code/CommTools/bsp/Common/crc.cpp` — CRC16：init=0x3692、poly=0x8408（LSB-first）
- `Code/CommTools/View/Component/DebugPage.qml` — XCOM 风格调试页
- `Doc/协议规范/IMU-用户协议.md` — 协议唯一事实来源；`指令解析方案.md` — 开发规范

## 记录索引

- 2026-10-10 [HexCommands 实现核对与修复报告](Doc/HexCommands-实现核对与修复报告.md) — 17 条指令全量核对、5 处修复、COM8 实测证据
- 2026-10-10 [XCOM 功能对照报告](Doc/XCOM功能对照报告.md) — DebugPage vs ATK-XCOM
- 2026-10-10 [波形页优化报告](Doc/波形页优化报告.md) — 卡顿三根因(整窗重绘/前删/隐藏页日志过滤)、Y轴自适应、模拟器float精度bug、自测钩子与实测数据
- 2026-10-10 [协议开发规范](Doc/协议开发规范.md)（项目内 `指令解析方案.md` 修复后快照）
