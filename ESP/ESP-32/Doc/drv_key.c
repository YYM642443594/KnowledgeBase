/**
 * @file drv_key.c
 * @author 杨镒铭 (642443594@qq.com)
 * @brief
 * @version V1.0.0
 * @date 2026-05-06
 *
 * @copyright Copyright (c) 2026
 *
 */

#include "drv_key.h"
#include "bsp_function.h"
#include "bsp_app.h"
#include "gd32f30x.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define KEY_PRESSED 1   /* 按键按下 */
#define KEY_UNPRESSED 0 /* 按键松开 */

#define KEY_SCAN_PERIOD_MS 20U

static unsigned int G_KeyTimeDouble = 50;
static unsigned int G_KeyTimeLong = 3000;
static unsigned int G_KeyTimeRepeat = 100;

typedef struct
{
    unsigned int GPIOxRCC;
    unsigned int GPIOxPort;
    unsigned int GPIOxPin;
} GDGPIOx_S, *pGDGPIOx_S;

static const GDGPIOx_S G_GDGPIOx[KEY_GPIO_PIN_MAX_E] = {
    {RCU_GPIOA, GPIOA, GPIO_PIN_8},
};

volatile unsigned char G_KeyFlag[KEY_COUNT]; /* 按键标志 */

/**
 * @brief 按键长按时间配置
 *
 * @param TimeMs 按键长按时间
 * @return int 0成功，EOF失败
 */
int DrvKeyTimeLongSet(unsigned int TimeMs)
{
    if (TimeMs < 0)
    {
        return EOF;
    }

    G_KeyTimeLong = TimeMs;
    return 0;
}

int DrvKeyGPIOPinxInit(GDKeyPIOPinx_E GDKeyPIOPinx)
{
    if (GDKeyPIOPinx >= KEY_GPIO_PIN_MAX_E)
        return EOF;
    /* enable the led clock */
    rcu_periph_clock_enable((rcu_periph_enum)G_GDGPIOx[GDKeyPIOPinx].GPIOxRCC);
    /* configure led GPIO port */
    gpio_init(G_GDGPIOx[GDKeyPIOPinx].GPIOxPort, GPIO_MODE_IPU, GPIO_OSPEED_50MHZ, G_GDGPIOx[GDKeyPIOPinx].GPIOxPin);

    return 0;
}

static unsigned char DrvKeyGetStateGet(unsigned char KeyIndex)
{
    if (KeyIndex == KEY_1)
    {
        if (gpio_input_bit_get(G_GDGPIOx[KEY_GPIO_PIN_PA8_E].GPIOxPort, G_GDGPIOx[KEY_GPIO_PIN_PA8_E].GPIOxPin) == 0)
        {
            return KEY_PRESSED;
        }
    }
    return KEY_UNPRESSED;
}

void DrvKeyTick(void)
{
    static unsigned char Count, i;
    static unsigned char CurrState[KEY_COUNT], PrevState[KEY_COUNT];
    static unsigned char S[KEY_COUNT];
    static unsigned short Time[KEY_COUNT]; /* 计数计时 */

    if ((BspUserDataGet()->ChargingState == CHARGING_E || BspUserDataGet()->ChargingState == CHARGE_COMPLETE_E) && BspPowerStateGet() == 0 && memcmp(BspProductInfoShadowGet()->DevInfo.HW, HARDWARE_504_C02, 3) == 0)
    {
        return;
    }

    for (i = 0; i < KEY_COUNT; i++)
    {
        if (Time[i] > 0)
        {
            Time[i]--;
        }
    }

    Count++;
    if (Count >= KEY_SCAN_PERIOD_MS)
    {
        Count = 0;

        for (i = 0; i < KEY_COUNT; i++)
        {
            PrevState[i] = CurrState[i];
            CurrState[i] = DrvKeyGetStateGet(i);

            if (CurrState[i] == KEY_PRESSED)
            {
                G_KeyFlag[i] |= KEY_HOLD;
            }
            else
            {
                G_KeyFlag[i] &= ~KEY_HOLD;
            }

            if (CurrState[i] == KEY_PRESSED && PrevState[i] == KEY_UNPRESSED)
            {
                G_KeyFlag[i] |= KEY_DOWN;
            }

            if (CurrState[i] == KEY_UNPRESSED && PrevState[i] == KEY_PRESSED)
            {
                G_KeyFlag[i] |= KEY_UP;
            }

            if (S[i] == 0)
            {
                if (CurrState[i] == KEY_PRESSED)
                {
                    Time[i] = G_KeyTimeLong;
                    S[i] = 1;
                }
            }
            else if (S[i] == 1)
            {
                if (CurrState[i] == KEY_UNPRESSED)
                {
                    Time[i] = G_KeyTimeDouble;
                    S[i] = 2;
                }
                else if (Time[i] == 0)
                {
                    Time[i] = G_KeyTimeRepeat;
                    G_KeyFlag[i] |= KEY_LONG;
                    S[i] = 4;
                }
            }
            else if (S[i] == 2)
            {
                if (CurrState[i] == KEY_PRESSED)
                {
                    G_KeyFlag[i] |= KEY_DOUBLE;
                    S[i] = 3;
                }
                else if (Time[i] == 0)
                {
                    G_KeyFlag[i] |= KEY_SINGLE;
                    S[i] = 0;
                }
            }
            else if (S[i] == 3)
            {
                if (CurrState[i] == KEY_UNPRESSED)
                {
                    S[i] = 0;
                }
            }
            else if (S[i] == 4)
            {
                if (CurrState[i] == KEY_UNPRESSED)
                {
                    S[i] = 0;
                }
                else if (Time[i] == 0)
                {
                    Time[i] = G_KeyTimeRepeat;
                    G_KeyFlag[i] |= KEY_REPEAT;
                    S[i] = 4;
                }
            }
        }
    }
}

unsigned char DrvKeyCheck(unsigned char KeyIndex, unsigned char Flag)
{
    if (KeyIndex >= KEY_COUNT)
        return 0;

    //__disable_irq();
    if (G_KeyFlag[KeyIndex] & Flag)
    {
        if (Flag != KEY_HOLD)
        {
            G_KeyFlag[KeyIndex] &= ~Flag;
        }
        return 1;
    }
    //__enable_irq();
    return 0;
}
