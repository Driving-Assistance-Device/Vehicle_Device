import lgpio

RED_LED  = 23
YELLOW_LED = 24
BLUE_LED = 25
BTN_0 = 17
BTN_1 = 22
BTN_2 = 27

gpio = None
def init_GPIO():
    global gpio
    gpio = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_output(gpio, BLUE_LED)
    lgpio.gpio_claim_output(gpio, YELLOW_LED)
    lgpio.gpio_claim_output(gpio, RED_LED)
    lgpio.gpio_claim_input(gpio, BTN_0)
    lgpio.gpio_claim_input(gpio, BTN_1)
    lgpio.gpio_claim_input(gpio, BTN_2)
    return gpio

def read_button(BTN):
    if lgpio.gpio_read(gpio, BTN):
        return True
    return False

# 1 -> ON, 0 -> OFF
def toggle_LED(LED, STATE):
    lgpio.gpio_write(gpio, LED, STATE)
    
def exit_GPIO():
    lgpio.gpiochip_close(gpio)
