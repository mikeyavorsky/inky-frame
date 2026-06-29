import gc
import time

import inky_helper as ih
import ota
from inky_frame import BLACK, BLUE, GREEN, WHITE
from machine import reset
# Uncomment the line for your Inky Frame display size
# from picographics import PicoGraphics, DISPLAY_INKY_FRAME_4 as DISPLAY  # 4.0"
from picographics import PicoGraphics, DISPLAY_INKY_FRAME as DISPLAY      # 5.7"
# from picographics import PicoGraphics, DISPLAY_INKY_FRAME_7 as DISPLAY  # 7.3"
# from picographics import \
#    DISPLAY_INKY_FRAME_SPECTRA_7 as DISPLAY  # 7.3" Spectra
from picographics import PicoGraphics

# Create a secrets.py with your Wifi details to be able to get the time
#
# secrets.py should contain:
# WIFI_SSID = "Your WiFi SSID"
# WIFI_PASSWORD = "Your WiFi password"

# A short delay to give USB chance to initialise
time.sleep(0.5)

# Setup for the display.
graphics = PicoGraphics(DISPLAY)
WIDTH, HEIGHT = graphics.get_bounds()
graphics.set_font("bitmap8")


def launcher():

    # Apply an offset for the Inky Frame 5.7".
    if HEIGHT == 448:
        y_offset = 20
    # Inky Frame 7.3"
    elif HEIGHT == 480:
        y_offset = 35
    # Inky Frame 4"
    else:
        y_offset = 0

    # Draws the menu
    graphics.set_pen(WHITE)
    graphics.clear()

    graphics.set_pen(BLUE)
    graphics.rectangle(0, 0, WIDTH, 50)
    graphics.set_pen(WHITE)
    title = "Launcher"
    title_len = graphics.measure_text(title, 4) // 2
    graphics.text(title, (WIDTH // 2 - title_len), 10, WIDTH, 4)

    graphics.set_pen(GREEN)
    graphics.rectangle(30, HEIGHT - (340 + y_offset), WIDTH - 100, 50)
    graphics.set_pen(1)
    graphics.text("A. NASA Picture of the Day", 35, HEIGHT - (325 + y_offset), 600, 3)

    graphics.set_pen(BLUE)
    graphics.rectangle(30, HEIGHT - (280 + y_offset), WIDTH - 150, 50)
    graphics.set_pen(1)
    graphics.text("B. Word Clock", 35, HEIGHT - (265 + y_offset), 600, 3)

    graphics.set_pen(GREEN)
    graphics.rectangle(30, HEIGHT - (220 + y_offset), WIDTH - 200, 50)
    graphics.set_pen(1)
    graphics.text("C. Daily XKCD", 35, HEIGHT - (205 + y_offset), 600, 3)

    graphics.set_pen(BLUE)
    graphics.rectangle(30, HEIGHT - (160 + y_offset), WIDTH - 250, 50)
    graphics.set_pen(1)
    graphics.text("D. Headlines", 35, HEIGHT - (145 + y_offset), 600, 3)

    graphics.set_pen(GREEN)
    graphics.rectangle(30, HEIGHT - (100 + y_offset), WIDTH - 300, 50)
    graphics.set_pen(1)
    graphics.text("E. Carbon Intensity", 35, HEIGHT - (85 + y_offset), 600, 3)

    graphics.set_pen(graphics.create_pen(220, 220, 220))
    graphics.rectangle(WIDTH - 100, HEIGHT - (340 + y_offset), 70, 50)
    graphics.rectangle(WIDTH - 150, HEIGHT - (280 + y_offset), 120, 50)
    graphics.rectangle(WIDTH - 200, HEIGHT - (220 + y_offset), 170, 50)
    graphics.rectangle(WIDTH - 250, HEIGHT - (160 + y_offset), 220, 50)
    graphics.rectangle(WIDTH - 300, HEIGHT - (100 + y_offset), 270, 50)

    graphics.set_pen(BLACK)
    note = "Hold A + E, then press Reset, to return to the Launcher"
    note_len = graphics.measure_text(note, 2) // 2
    graphics.text(note, (WIDTH // 2 - note_len), HEIGHT - 30, 600, 2)

    ih.led_warn.on()
    graphics.update()
    ih.led_warn.off()

    # Now we've drawn the menu to the screen, we wait here for the user to select an app.
    # Then once an app is selected, we set that as the current app and reset the device and load into it.

    # You can replace any of the included examples with one of your own,
    # just replace the name of the app in the line "ih.update_last_app("nasa_apod")"

    while True:
        if ih.inky_frame.button_a.read():
            ih.inky_frame.button_a.led_on()
            ih.update_state("nasa_apod")
            time.sleep(0.5)
            reset()
        if ih.inky_frame.button_b.read():
            ih.inky_frame.button_b.led_on()
            ih.update_state("word_clock")
            time.sleep(0.5)
            reset()
        if ih.inky_frame.button_c.read():
            ih.inky_frame.button_c.led_on()
            ih.update_state("daily_xkcd")
            time.sleep(0.5)
            reset()
        if ih.inky_frame.button_d.read():
            ih.inky_frame.button_d.led_on()
            ih.update_state("news_headlines")
            time.sleep(0.5)
            reset()
        if ih.inky_frame.button_e.read():
            ih.inky_frame.button_e.led_on()
            ih.update_state("carbon_intensity")
            time.sleep(0.5)
            reset()


# Turn any LEDs off that may still be on from last run.
ih.clear_button_leds()
ih.led_warn.off()

if ih.inky_frame.button_a.read() and ih.inky_frame.button_e.read():
    launcher()

ih.clear_button_leds()

try:
    from secrets import WIFI_PASSWORD, WIFI_SSID
    ih.network_connect(WIFI_SSID, WIFI_PASSWORD)
except ImportError:
    print("Create secrets.py with your WiFi credentials")

# Check for new code on every wake. Resets the device if an update is applied,
# otherwise falls through. Best-effort - a failure here (no WiFi, GitHub down)
# just means we run the existing code this cycle.
try:
    ota.check_and_update()
except Exception as e:
    print("OTA check failed:", e)

if ih.file_exists("state.json"):
    # Loads the JSON and launches the app
    print("load state")
    ih.load_state()
    ih.launch_app(ih.state["run"])

    # Passes the the graphics object from the launcher to the app
    ih.app.graphics = graphics
    ih.app.WIDTH = WIDTH
    ih.app.HEIGHT = HEIGHT

else:
    launcher()

# Get some memory back, we really need it!
gc.collect()

# The main loop executes the update and draw function from the imported app,
# and then goes to sleep ZzzzZZz

file = ih.file_exists("state.json")

print(file)

# We reached a clean running state - confirm any pending update so it won't be
# rolled back on the next boot.
ota.mark_boot_ok()

try:
    while True:
        ih.app.update()
        ih.led_warn.on()
        ih.app.draw()
        ih.led_warn.off()
        print("sleeping")
        ih.sleep(ih.app.UPDATE_INTERVAL)
except Exception as e:
    # Self-healing recovery: don't hard-crash. Try to pull a fix, then deep-sleep
    # so the device wakes back into boot.py -> main.py for another shot.
    print("fatal:", e)
    try:
        ota.check_and_update()
    except Exception as oe:
        print("OTA recovery poll failed:", oe)
    try:
        ih.sleep(5)
    except Exception:
        time.sleep(300)
    reset()

