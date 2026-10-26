/**
 * @file drv_key.h
 * @author 杨镒铭 (642443594@qq.com)
 * @brief
 * @version V1.0.0
 * @date 2026-05-06
 *
 * @copyright Copyright (c) 2026
 *
 */

#ifndef __DRV_KEY_H__
#define __DRV_KEY_H__
#ifdef __cplusplus
extern "C"
{
#endif

#define KEY_COUNT 1 /* 按键个数 */

#define KEY_1 0

#define KEY_HOLD 0x01   /* 按住不放 */
#define KEY_DOWN 0x02   /* 按下时刻 */
#define KEY_UP 0x04     /* 松开时刻 */
#define KEY_SINGLE 0x08 /* 单击 */
#define KEY_DOUBLE 0x10 /* 双击 */
#define KEY_LONG 0x20   /* 长按 */
#define KEY_REPEAT 0x40 /* 重复 */

    typedef enum
    {
        KEY_GPIO_PIN_PA8_E, /* KEY0 */
        KEY_GPIO_PIN_MAX_E, /* 未定义 */
    } GDKeyPIOPinx_E;

    /**
     * @brief 按键长按时间配置
     *
     * @param TimeMs 按键长按时间
     * @return int 0成功，EOF失败
     */
    int DrvKeyTimeLongSet(unsigned int TimeMs);

    int DrvKeyGPIOPinxInit(GDKeyPIOPinx_E GDKeyPIOPinx);

    void DrvKeyTick(void);

    unsigned char DrvKeyCheck(unsigned char KeyIndex, unsigned char Flag);

#ifdef __cplusplus
}
#endif /* __cplusplus */
#endif /* __DRV_KEY_H__ */
