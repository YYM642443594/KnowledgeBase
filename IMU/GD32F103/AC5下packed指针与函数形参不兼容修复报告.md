# AC5 下 __packed 结构成员指针与函数形参不兼容修复报告（2026-10-23）

## 一、测试现象

bsp_data_interaction.c 推送帧填充逻辑重构后（提取 3 个共用填充助手函数），
Keil AC5（V5.06 update 7）编译报 **24 个同型错误**：

```text
error: #167: argument of type "__packed float *" is incompatible
       with parameter of type "float *"
```

全部指向新助手函数的调用点与直连 memcpy：

```c
BspPushFillImuNorm(OriginalData.accel, OriginalData.gyro, &OriginalData.temp, pArithmeticData);
memcpy(MasterData3DGraphics.accel, pArithmeticData->Accel, sizeof(MasterData3DGraphics.accel));
```

## 二、根因分析

推送目标结构体均为 `__packed struct`（协议帧布局，禁止编译器填充）：

```c
typedef __packed struct
{
    unsigned char ack_result;      /* 偏移 0  */
    unsigned long long time;       /* 偏移 1  */
    unsigned short int frequency;  /* 偏移 9  */
    float accel[3];                /* 偏移 11 ←★ 非 4 字节对齐 */
    ...
} MasterData3DGraphics_S;
```

- **packed 结构不做对齐填充**，成员实际偏移由前序成员逐字节累加
  （上例 `accel` 偏移 11），首地址普遍非 4 字节对齐
- AC5 对 packed 结构成员数组取地址/退化得到的指针类型是
  **`__packed float *`**（不是 `float *`）——该类型告知编译器
  "目标可能非对齐"，经它访问自动生成非对齐安全代码
- ARMCC 类型规则：`__packed T *` **不可隐式转换**为 `T *`，
  连 `void *` 也不行 → 传给 `float *`/`void *restrict` 形参即报 #167

**为什么旧代码从未报错**：旧实现全部逐字段赋值
（`OriginalData.accel[0] = pArithmeticData->Accel[0];`），左值经
`__packed float *` 元素访问，从不取数组成员地址传参——
**编译器一直在背后做非对齐安全访问，重构把这段"隐式行为"显式化时踩坑**。

## 三、修复方案

### 1. 助手形参声明为 `__packed float *`（正确解）

```c
static void BspPushFillImuNorm(__packed float *pAccel, __packed float *pGyro,
                               __packed float *pTemp, const pArithmeticData_S pSrc)
{
    for (int i = 0; i < 3; i++)
    {
        pAccel[i] = pSrc->Accel[i];  /* 编译器生成非对齐安全代码,与原逐字段赋值同类 */
        pGyro[i] = pSrc->Gyro[i];
    }
    pAccel[3] = sqrtf(...);          /* 模值槽位 */
}
```

- 源参数 `pArithmeticData`（普通结构）不受影响，读写两侧类型独立
- **与原逐字段赋值编译语义完全一致**——不是新行为，是把原行为显式化

### 2. memcpy 目标显式加 `(void *)` 转换

```c
memcpy((void *)MasterData3DGraphics.accel, pArithmeticData->Accel,
       sizeof(MasterData3DGraphics.accel));  /* 逐字节拷贝,对齐无关,天然安全 */
```

`__packed` 指针 → `void *` 允许**显式**转换；memcpy 本身逐字节搬运，
不假设对齐，拷贝结果与逐字段赋值逐位一致。

## 四、风险辨析（为什么不用 `(float *)` 强转）

```c
/* 错误解(编译能过,留隐患): */
BspPushFillImuNorm((float *)OriginalData.accel, ...);
```

- 强转成普通 `float *` 后，编译器按 **4 字节对齐假设**生成 LDR/STR 字访问，
  甚至可能向量化为 LDM/STM（这些指令**不允许**非对齐地址）→ 非对齐 HardFault
  或数据损坏
- 行为依赖 `CCR.UNALIGN_TRP` 配置与编译器优化决策，属于不可移植的未定义行为

## 五、约束规范（后续红线）

1. **跨函数传递 `__packed struct` 成员指针，形参必须声明为 `__packed T *`**
2. `__packed` 指针传给 memcpy 等期望 `void *` 的接口，必须**显式 `(void *)` 转换**
3. **严禁 `(float *)` 强转 packed 成员指针**——非对齐字访问隐患
4. packed 结构是协议帧布局：只在**组包/拆包边界**使用；
   内部算法数据结构保持自然对齐（如 ArithmeticData_S），避免 packed 传染
5. 提取共用助手函数收敛重复代码时，注意 packed 成员地址传参这一
   逐字段赋值时代不存在的坑——AC5 的 #167 在编译期全部拦下，
   不会带病上线（本例 24 错即编译期拦截）
