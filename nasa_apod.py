import gc
import time
from urllib import urequest

import jpegdec
from inky_frame import BLACK, RED, WHITE
from ujson import load

gc.collect()

graphics = None
WIDTH = 600
HEIGHT = 448

FILENAME = "nasa-apod-daily"

# A Demo Key is used in this example and is IP rate limited. You can get your own API Key from https://api.nasa.gov/
API_URL = "https://api.nasa.gov/planetary/apod?api_key=YWpGuepcYi4pxPdN05buk4KFTJFVaLm6lqELdGYy"

# Length of time between updates in minutes.
# Frequent updates will reduce battery life!
UPDATE_INTERVAL = 240

# Added to the RTC (which NTP sets to UTC) when stamping the caption.
# -4*3600 = EDT, -5*3600 = EST, 0 = UTC.
TZ_OFFSET = -4 * 3600

# Variable for storing the NASA APOD Title
apod_title = None
last_updated = None


def show_error(text):
    graphics.set_pen(RED)
    graphics.rectangle(0, 10, WIDTH, 35)
    graphics.set_pen(BLACK)
    graphics.text(text, 5, 16, 400, 2)


def update():
    print("update")
    global apod_title, last_updated

    if HEIGHT == 448:
        # Image for Inky Frame 5.7
        IMG_URL = "https://pimoroni.github.io/feed2image/nasa-apod-daily.jpg"
    elif HEIGHT == 400:
        # Image for Inky Frame 4.0
        IMG_URL = "https://pimoroni.github.io/feed2image/nasa-apod-640x400-daily.jpg"
    elif HEIGHT == 480:
        # Image for Inky Frame 7.3
        IMG_URL = "https://pimoroni.github.io/feed2image/nasa-apod-800x480-daily.jpg"

    try:
        # Grab the data
        print("starting socket")
        socket = urequest.urlopen(API_URL)
        print("socket open")
        gc.collect()
        j = load(socket)
        socket.close()
        apod_title = j["title"]
        # apod_title = "Government Shutdown"
        print(apod_title)
        gc.collect()
    except OSError as e:
        print(e)
        apod_title = "Image Title Unavailable"

    try:
        # Grab the image
        socket = urequest.urlopen(IMG_URL)

        gc.collect()

        data = bytearray(1024)
        with open(FILENAME, "wb") as f:
            while True:
                if socket.readinto(data) == 0:
                    break
                f.write(data)
        socket.close()
        del data
        gc.collect()
    except OSError as e:
        print(e)
        show_error("Unable to download image")

    t = time.localtime(time.time() + TZ_OFFSET)
    last_updated = "%04d-%02d-%02d %02d:%02d" % (t[0], t[1], t[2], t[3], t[4])


def draw():
    jpeg = jpegdec.JPEG(graphics)
    gc.collect()  # For good measure...

    graphics.set_pen(WHITE)
    graphics.clear()

    try:
        jpeg.open_file(FILENAME)
        jpeg.decode()
    except OSError:
        graphics.set_pen(RED)
        graphics.rectangle(0, (HEIGHT // 2) - 20, WIDTH, 40)
        graphics.set_pen(BLACK)
        graphics.text("Unable to display image!", 5, (HEIGHT // 2) - 15, WIDTH, 2)
        graphics.text("Check your network settings in secrets.py", 5, (HEIGHT // 2) + 2, WIDTH, 2)

    graphics.set_pen(WHITE)
    graphics.rectangle(0, HEIGHT - 25, WIDTH, 25)
    graphics.set_pen(BLACK)
    stamp = last_updated or ""
    stamp_w = graphics.measure_text(stamp, 2) if stamp else 0
    # Reserve space for the right-aligned timestamp; title wraps within the rest.
    title_w = WIDTH - 10 - (stamp_w + 10 if stamp_w else 0)
    graphics.text(apod_title, 5, HEIGHT - 20, title_w, 2)
    if stamp:
        graphics.text(stamp, WIDTH - 5 - stamp_w, HEIGHT - 20, WIDTH, 2)

    gc.collect()

    graphics.update()

