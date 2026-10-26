# 小区自动售水机

[TOC]



# 1 协议概述

​	本协议用于设备、客户端与云服务器之间通过` MQTT `协议进行通信。

**特点：**

- 基于发布/订阅模式
- `JSON` 数据格式
- 支持设备认证
- 支持实时消息通信
- 支持命令下发
- 支持状态上报
- 支持心跳检测



# 2 `MQTT`连接参数



# 3 `Topic`规范&定义

## 3.1 `Topic`规范

​	`Topic`命名格式：

```json

```



# 4 通用`JSON`数据格式

​	所有`MQTT`消息统一采用如下结构：

```json
{
  "SN": "AWM00001",
  "Time": "2026-05-14 00:00:00",
  "Version": "V1.0.0.0",
  "Data": {
	"OrderType":"EquipmentStatusData",
    "OrderData":{
            
	}
  }
}
```



# 5 字段说明

## 5.1 通用`JSON`格式字段说明

| 字段        | 类型   | 说明           |
| ----------- | ------ | -------------- |
| SN          | String | 设备SN号       |
| Time        | String | 时间           |
| Version     | String | 设备固件版本   |
| Data        | Object | 业务数据       |
| `OrderType` | String | 指令类别       |
| `OrderData` | Object | 指令负载的数据 |
|             |        |                |



### 5.1.1 业务数据字段说明

#### 5.1.1.1 指令类型字段说明

​	指令字段类型说明如下：

| 字段                            | 类型   | 说明                          |
| ------------------------------- | ------ | ----------------------------- |
| `EquipmentStatusData`           | String | 设备状态数据                  |
| `UserCardData`                  | String | 用户卡数据                    |
| `AdvertisingLight`              | String | 广告灯开启时间控制            |
| `ImmersionInUltravioletRays`    | String | 浸没紫外线开启时间控制        |
| `HeatingAntiFreezing`           | String | 加热防冻温度控制              |
| `WorkMode`                      | String | 工作模式控制                  |
| `TestMode`                      | String | 测试模式控制                  |
| `AI0`                           | String | 模拟量0配置                   |
| `AI1`                           | String | 模拟量1配置                   |
| `Ozonator`                      | String | 臭氧发生器控制                |
| `AmountRecoveryTime`            | String | 金额回收时间配置/查询         |
| `WaterLightDoorMagnetic`        | String | 售水灯与门磁延迟时间配置/查询 |
| `WashingTime`                   | String | 冲洗时间配置/查询             |
| `RinseInterval`                 | String | 冲洗间隔配置/查询             |
| `DurationOfWaterFlushing`       | String | 水满冲洗时长配置/查询         |
| `WaterFillingFlushInterval`     | String | 水满冲洗间隔配置/查询         |
| `TempLowerLimitAlarm`           | String | 温度下限报警配置/查询         |
| `PureWaterLevelUpperLimitAlarm` | String | 纯水上限报警配置/查询         |
| `UpperLimitWaterLevelAlarm`     | String | 原水上限报警配置/查询         |
| `FilterElement`                 | String | 滤芯更换流量配置/查询         |
| `OvercurrentUltravioletLamp`    | String | 过流紫光灯寿命配置/查询       |
| `SubmergedUVLamp`               | String | 浸没紫光灯寿命配置/查询       |
| `Volume`                        | String | 设置配置/查询                 |
| `PipelineDisinfectionDelay`     | String | 延时启动管道消杀时间配置/查询 |
| `PipelineDisinfectionTime`      | String | 管道消杀时长配置/查询         |
| `FlowCorrectionFactor`          | String | 流量校对系数配置/查询         |
| `PulseCount1`                   | String | 额定流量1脉冲数配置/查询      |
| `PulseCount2`                   | String | 额定流量2脉冲数配置/查询      |
| `PulseCount3`                   | String | 额定流量3脉冲数配置/查询      |
| `RatedValue1`                   | String | 额定流量1的额定值配置/查询    |
| `RatedValue2`                   | String | 额定流量2的额定值配置/查询    |
| `RatedValue3`                   | String | 额定流量3的额定值配置/查询    |
| `WeChatPrice`                   | String | 微信扫码支付单价              |
| `AlipayPrice`                   | String | 支付宝扫码支付单价            |
| `ReportedTime`                  | String | 设备主动上报时间配置/查询     |



#### 5.1.1.2 指令负载的数据字段说明

| 字段                      | 类型           | 说明                                                  |
| ------------------------- | -------------- | ----------------------------------------------------- |
| `UserCardID`              | String         | 用户卡号                                              |
| `UserCardBalance`         | float          | 用户卡余额                                            |
| `SingleTransactionAmount` | float          | 单次消费金额                                          |
| `SingleWaterVolume`       | float          | 单次罐装的水量                                        |
| `UserCardTime`            | String         | 用户卡数据时间                                        |
| `IntValue`                | int            |                                                       |
| `FloatValue`              | float          |                                                       |
| `Year`                    | unsigned short | 年                                                    |
| `Month`                   | unsigned short | 月                                                    |
| `Day`                     | unsigned short | 日                                                    |
| `Hour`                    | unsigned short | 秒                                                    |
| `minute`                  | unsigned short | 分                                                    |
| `second`                  | unsigned short | 秒                                                    |
| `OrderType`               | String         | off：关闭    on：开启  Query：查询    Configure：配置 |
| `Supplier`                | String         | 供应商                                                |
| `Temp`                    | float          | 设备温度                                              |
| `MeterEnergy`             | float          | 电表电量                                              |
| `MWV`                     | float          | 水表水量                                              |
| `CanWaterVolTotal`        | float          | 累计罐装水量                                          |
| `TotalWaterVolume`        | float          | 累计总水量                                            |
| `OtherWaterTotal`         | float          | 累计其它水量                                          |
| `UVL`                     | unsigned int   | 过流紫光灯累计工作时长                                |
| `Conductivity`            | float          | 电导率数据                                            |
| `NumericInputState`       | unsigned short | 数字点输入状态                                        |
| `NumericOutputState`      | unsigned short | 数字点输出状态                                        |
| `WP_MCRT`                 | unsigned int   | 制水泵最大连续工作时长                                |
| `RSSI`                    | unsigned char  | 网络信号强度                                          |
| `ICCID`                   | String         | 流量卡号                                              |
| `SimCardStatus`           | unsigned char  | 流量卡状态                                            |
| `SIMCardExpiryDate`       | String         | 流量卡到期日期                                        |
| `IMEI`                    | String         | `IMEI`码                                              |
| `DWSV`                    | float          | 日累计销售水量                                        |
| `DEC`                     | float          | 日累计用电量                                          |
| `DWC`                     | float          | 日累计消耗水量                                        |



## 5.2 通用配置与主动上报字段说明

### 5.2.1 时分秒配置与查询

支持配置与查询时分秒的指令如下：

- 浸没紫外线开启时间控制
- 臭氧发生器控制

| 字段        | 单位 | 说明      |
| ----------- | ---- | --------- |
| `OrderType` |      | 配置/查询 |
| `Hour`      | 时   |           |
| `minute`    | 分   |           |
| `second`    | 秒   |           |



### 5.2.2 时分配置与查询

支持配置与查询时分的指令如下：

- 广告灯开启时间控制

| 字段        | 单位 | 说明      |
| ----------- | ---- | --------- |
| `OrderType` |      | 配置/查询 |
| `Hour`      | 时   |           |
| `minute`    | 分   |           |



### 5.2.3 分配置与查询

支持配置与查询分的指令如下：

- 设备主动上报时间 
- 水满冲洗间隔 
- 冲洗间隔

| 字段        | 单位 | 说明      |
| ----------- | ---- | --------- |
| `OrderType` |      | 配置/查询 |
| `minute`    | 分钟 |           |



### 5.2.4 秒配置与查询

支持配置与查询秒的指令如下：

- 延时启动管道消杀时间
- 管道消杀时长
- 水满冲洗时长
- 冲洗时间
-  售水灯与门磁延迟时间
- 金额回收时间

| 字段        | 单位 | 说明      |
| ----------- | ---- | --------- |
| `OrderType` |      | 配置/查询 |
| `second`    | 秒   |           |



### 5.2.5 整数值配置与查询

支持配置与查询整数值的指令如下：

- 温度下限值
- 纯水上限值
- 原水上限值
- 滤芯更换流量值
- 过流紫光灯寿命值
- 浸没紫光灯寿命值
- 音量值
- 流量校对系数值
- 额定流量1/2/3脉冲数
- 额定流量1/2/3的额定值
- 加热防冻温度控制
- 工作模式控制
  - 0：自动模式  
  - 1：测机模式 
  - 2：停止模式

| 字段        | 单位 | 说明      |
| ----------- | ---- | --------- |
| `OrderType` |      | 配置/查询 |
| `IntValue`  |      |           |



### 5.2.6 浮点数值配置与查询

支持配置与查询整浮点的指令如下：

| 字段         | 单位 | 说明      |
| ------------ | ---- | --------- |
| `OrderType`  |      | 配置/查询 |
| `FloatValue` |      |           |



### 5.2.6 开关控制配置与查询

支持配置与查询开关控制的指令如下：

- 测机控制
- 管道消杀控制

| 字段        | 单位 | 说明      |
| ----------- | ---- | --------- |
| `OrderType` |      | 开启/关闭 |



### 5.2.7 模拟量配置与查询

支持配置与查询模拟量的指令如下：

- 模拟量0配置
- 模拟量1配置

| 字段         | 单位 | 说明          |
| ------------ | ---- | ------------- |
| `OrderType`  |      | 配置/查询     |
| `IntValue`   |      | 模拟量0/1配置 |
| `FloatValue` |      | 模拟量标定值  |
| `FloatValue` |      | 模拟量量程值  |



### 5.2.8 设备状态数据

| 字段    | 偏移(字节) | 长度(字节) |       类型        | 单位  | 说明                   |
| ------- | :--------: | :--------: | :---------------: | :---: | ---------------------- |
|         |            |     4      |       float       |   ℃   | 设备温度               |
|         |            |     4      |       float       |  kWh  | 电表电量               |
|         |            |     4      |       float       | 吨(t) | 水表水量               |
|         |            |     4      |       float       |   L   | 累计罐装水量           |
|         |            |     4      |       float       |   T   | 累计总水量             |
|         |            |     4      |       float       |   T   | 累计其它水量           |
|         |            |     4      |   unsigned int    | 分钟  | 过流紫光灯累计工作时长 |
|         |            |     4      |       float       |       | 电导率数据             |
|         |            |     2      |  unsigned short   |       | 数字点输入状态         |
|         |            |     2      |  unsigned short   |       | 数字点输出状态         |
|         |            |            |   unsigned int    | 分钟  | 制水泵最大连续工作时长 |
|         |            |            |   unsigned char   |       | 网络信号强度           |
|         |            |            | unsigned char[32] |       | 流量卡号               |
|         |            |            |   unsigned char   |       | 流量卡状态             |
|         |            |            |   unsigned int    |       | 流量卡到期日期         |
|         |            |            | unsigned char[32] |       | `IMEI`码               |
|         |            |            |                   |   L   | 日累计销售水量         |
|         |            |            |                   |  kWh  | 日累计用电量           |
|         |            |            |                   |   L   | 日累计消耗水量         |
| `CRC16` |            |            |  unsigned short   |       |                        |





# 6 示例

## 6.1 时分秒配置与查询

### 6.1.1 配置

- 客户端发送如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"Ozonator",
      "OrderData":{
              "OrderType":"Configure",
              "Hour":12,
          	"minute":12,
          	"second":12
  	}
    }
  }
  ```

- 设备端回复如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"Ozonator",
      "OrderData":{
  	}
    }
  }
  ```



### 6.1.2 查询

- 客户端发送如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"Ozonator",
      "OrderData":{
              "OrderType":"Query",
  	}
    }
  }
  ```

- 设备端回复如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"Ozonator",
      "OrderData":{
              "Hour":12,
          	"minute":12,
          	"second":12
  	}
    }
  }
  ```

  

## 6.2 时分配置与查询

### 6.2.1 配置

- 客户端发送如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"AdvertisingLight",
      "OrderData":{
              "OrderType":"Configure",
          	 "Hour":12,
          	"minute":12,
  	}
    }
  }
  ```

- 设备端回复如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"AdvertisingLight",
      "OrderData":{
  	}
    }
  }
  ```

  

### 6.2.2 查询

- 客户端发送如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"AdvertisingLight",
      "OrderData":{
              "OrderType":"Query",
  	}
    }
  }
  ```

- 设备端回复如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"Ozonator",
      "OrderData":{
              "Hour":12,
          	"minute":12,
  	}
    }
  }
  ```

  

## 6.3 秒配置与查询

### 6.3.1 配置

- 客户端发送如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"AmountRecoveryTime",
      "OrderData":{
              "OrderType":"Configure",
          	"second":12
  	}
    }
  }
  ```

- 设备端回复如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"AmountRecoveryTime",
      "OrderData":{
  	}
    }
  }
  ```

  

### 6.3.2 查询

- 客户端发送如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"AmountRecoveryTime",
      "OrderData":{
              "OrderType":"Query",
  	}
    }
  }
  ```

- 设备端回复如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"AmountRecoveryTime",
      "OrderData":{
          	"second":12
  	}
    }
  }
  ```

  

## 6.4 整数值配置与查询

### 6.4.1 配置

- 客户端发送如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"WorkMode",
      "OrderData":{
              "OrderType":"Configure",
          	"IntValue":0
  	}
    }
  }
  ```

- 设备端回复如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"WorkMode",
      "OrderData":{
  	}
    }
  }
  ```

  

### 6.4.2 查询

- 客户端发送如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"AmountRecoveryTime",
      "OrderData":{
              "OrderType":"WorkMode",
  	}
    }
  }
  ```

- 设备端回复如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"WorkMode",
      "OrderData":{
          	"IntValue":0
  	}
    }
  }
  ```

  

## 6.5 浮点数值配置与查询

### 6.5.1 配置

- 客户端发送如下：

  ```json
  
  ```

- 设备端回复如下：

  ```json
  
  ```

  

### 6.5.2 查询

- 客户端发送如下：

  ```json
  
  ```

- 设备端回复如下：

  ```json
  
  ```

  

## 6.6 开关控制配置与查询

- 客户端发送如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"TestMode",
      "OrderData":{
              "OrderType":"off",
  	}
    }
  }
  ```

- 设备端回复如下：

  ```json
  {
    "SN": "AWM00001",
    "Time": "2026-05-14 00:00:00",
    "Version": "V1.0.0.0",
    "Data": {
  	"OrderType":"TestMode",
      "OrderData":{
  	}
    }
  }
  ```

  

## 6.7 模拟量配置与查询

### 6.7.1 配置

- 客户端发送如下：

  ```json
  
  ```

- 设备端回复如下：

  ```json
  
  ```

### 6.7.2 查询

- 客户端发送如下：

  ```json
  
  ```

- 设备端回复如下：

  ```json
  
  ```

  















