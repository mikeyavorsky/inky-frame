import json
import math
import os
import time

import inky_frame
import network
from machine import PWM, Pin, Timer
from pcf85063a import PCF85063A
from pimoroni_i2c import PimoroniI2C

# Pin setup for VSYS_HOLD needed to sleep and wake.
HOLD_VSYS_EN_PIN = 2
hold_vsys_en_pin = Pin(HOLD_VSYS_EN_PIN, Pin.OUT)

# intialise the pcf85063a real time clock chip
I2C_SDA_PIN = 4
I2C_SCL_PIN = 5
i2c = PimoroniI2C(I2C_SDA_PIN, I2C_SCL_PIN, 100000)
rtc = PCF85063A(i2c)

led_warn = Pin(6, Pin.OUT)

# set up for the network LED
network_led_pwm = PWM(Pin(7))
network_led_pwm.freq(1000)
network_led_pwm.duty_u16(0)


# set the brightness of the network led
def network_led(brightness):
    if quiet_hours():
        brightness = 0
    brightness = max(0, min(100, brightness))  # clamp to range
    # gamma correct the brightness (gamma 2.8)
    value = int(pow(brightness / 100.0, 2.8) * 65535.0 + 0.5)
    network_led_pwm.duty_u16(value)


network_led_timer = Timer(-1)
network_led_pulse_speed_hz = 1
network_led_mode = 0  # 0 = off, 1 = pulsing, 2 = connected
warn_led_requested = False


def _weekday(year, month, day):
    """Return day of week with Sunday == 0 (Gregorian calendar)."""
    offsets = (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)
    if month < 3:
        year -= 1
    return (year + year // 4 - year // 100 + year // 400
            + offsets[month - 1] + day) % 7


def quiet_hours(now=None):
    """Whether the current UTC RTC time falls between 10pm and 7am ET."""
    if now is None:
        now = time.localtime()
    year, month, day, utc_hour = now[0], now[1], now[2], now[3]

    # U.S. daylight time runs from 07:00 UTC on the second Sunday in March
    # until 06:00 UTC on the first Sunday in November.
    march_sunday = 8 + ((7 - _weekday(year, 3, 8)) % 7)
    november_sunday = 1 + ((7 - _weekday(year, 11, 1)) % 7)
    daylight = False
    if 3 < month < 11:
        daylight = True
    elif month == 3:
        daylight = day > march_sunday or (
            day == march_sunday and utc_hour >= 7
        )
    elif month == 11:
        daylight = day < november_sunday or (
            day == november_sunday and utc_hour < 6
        )

    eastern_hour = (utc_hour + (-4 if daylight else -5)) % 24
    return eastern_hour >= 22 or eastern_hour < 7


def network_led_callback(_t):
    quiet = quiet_hours()
    led_warn.value(1 if warn_led_requested and not quiet else 0)
    if quiet or network_led_mode == 0:
        network_led_pwm.duty_u16(0)
    elif network_led_mode == 1:
        # Pulse while connecting, unless the local quiet window is active.
        brightness = (math.sin(
            time.ticks_ms() * math.pi * 2
            / (1000 / network_led_pulse_speed_hz)
        ) * 40) + 60
        value = int(pow(brightness / 100.0, 2.8) * 65535.0 + 0.5)
        network_led_pwm.duty_u16(value)
    else:
        network_led_pwm.duty_u16(30000)


def _start_led_timer(period):
    network_led_timer.deinit()
    network_led_timer.init(
        period=period, mode=Timer.PERIODIC, callback=network_led_callback
    )


def set_warn_led(enabled):
    """Set the warning LED, honoring Eastern-time quiet hours."""
    global warn_led_requested
    warn_led_requested = enabled
    network_led_callback(None)
    if network_led_mode == 0:
        if enabled:
            _start_led_timer(1000)
        else:
            network_led_timer.deinit()


def show_network_connected():
    """Show steady network status and reevaluate quiet hours each second."""
    global network_led_mode
    network_led_mode = 2
    network_led_callback(None)
    _start_led_timer(1000)


# set the network led into pulsing mode
def pulse_network_led(speed_hz=1):
    global network_led_mode, network_led_pulse_speed_hz
    network_led_mode = 1
    network_led_pulse_speed_hz = speed_hz
    network_led_callback(None)
    _start_led_timer(50)


# turn off the network led and disable any pulsing animation that's running
def stop_network_led():
    global network_led_mode
    network_led_mode = 0
    if warn_led_requested:
        _start_led_timer(1000)
    else:
        network_led_timer.deinit()
    network_led_pwm.duty_u16(0)


def sleep(t):
    # Time to have a little nap until the next update
    rtc.clear_timer_flag()
    rtc.set_timer(t, ttp=rtc.TIMER_TICK_1_OVER_60HZ)
    rtc.enable_timer_interrupt(True)

    # Set the HOLD VSYS pin to an input
    # this allows the device to go into sleep mode when on battery power.
    hold_vsys_en_pin.init(Pin.IN)

    # Regular time.sleep for those powering from USB
    time.sleep(60 * t)


# Turns off the button LEDs
def clear_button_leds():
    inky_frame.button_a.led_off()
    inky_frame.button_b.led_off()
    inky_frame.button_c.led_off()
    inky_frame.button_d.led_off()
    inky_frame.button_e.led_off()


def network_connect(SSID, PSK):
    # Enable the Wireless
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # Number of attempts to make before timeout
    max_wait = 10

    # Sets the Wireless LED pulsing and attempts to connect to your local network.
    pulse_network_led()
    wlan.config(pm=0xa11140)  # Turn WiFi power saving off for some slow APs
    wlan.connect(SSID, PSK)

    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print("waiting for connection...")
        time.sleep(1)

    stop_network_led()

    # Handle connection error. Switches the Warn LED on.
    if wlan.status() != 3:
        set_warn_led(True)
    else:
        show_network_connected()


state = {"run": None}
app = None


def file_exists(filename):
    try:
        return (os.stat(filename)[0] & 0x4000) == 0
    except OSError:
        return False


def clear_state():
    if file_exists("state.json"):
        os.remove("state.json")


def save_state(data):
    with open("/state.json", "w") as f:
        f.write(json.dumps(data))
        f.flush()


def load_state():
    global state
    data = json.loads(open("/state.json", "r").read())
    if type(data) is dict:
        state = data


def update_state(running):
    global state
    state["run"] = running
    save_state(state)


def launch_app(app_name):
    global app
    app = __import__(app_name)
    print(app)
    update_state(app_name)
