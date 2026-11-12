#include <stdint.h>

#define LED_REG ((volatile uint32_t *)0x40000000u)
void set_led(uint32_t value) {
    *LED_REG = value;
}
