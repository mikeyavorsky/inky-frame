import gc
import time
import os
import json
from urllib import urequest

import jpegdec
from inky_frame import BLACK, RED, WHITE
from ujson import load

gc.collect()

graphics = None
WIDTH = 600
HEIGHT = 448

FILENAME = "apod-image.jpg"
METADATA = "apod-image.json"
FEED_ROOT = "https://raw.githubusercontent.com/mikeyavorsky/inky-frame/main/assets/apod/"

# Length of time between updates in minutes.
# Frequent updates will reduce battery life!
UPDATE_INTERVAL = 24 * 60

# Added to the RTC (which NTP sets to UTC) when stamping the caption.
# -4*3600 = EDT, -5*3600 = EST, 0 = UTC.
TZ_OFFSET = -4 * 3600

# Variable for storing the NASA APOD Title
apod_title = None
last_updated = None


def update():
    print("update")
    global apod_title, last_updated

    # Restore the caption paired with the last successful image on failure.
    try:
        with open(METADATA) as f:
            cached = load(f)
        apod_title = cached["title"]
        last_updated = cached["updated"]
    except (OSError, ValueError, KeyError):
        apod_title = "APOD unavailable"

    socket = None
    try:
        socket = urequest.urlopen(FEED_ROOT + "feed.json")
        feed = load(socket)
        socket.close()
        socket = None
        image_name = feed["images"][str(HEIGHT)]
        if "/" in image_name or not image_name.endswith(".jpg"):
            raise ValueError("Invalid APOD image filename")
        socket = urequest.urlopen(FEED_ROOT + image_name)
        data = bytearray(1024)
        with open(FILENAME + ".new", "wb") as f:
            while True:
                count = socket.readinto(data)
                if not count:
                    break
                f.write(memoryview(data)[:count])
        socket.close()
        socket = None
        del data
        gc.collect()
        # Reject truncated/non-JPEG downloads before replacing the cached image.
        with open(FILENAME + ".new", "rb") as f:
            if f.read(2) != b"\xff\xd8":
                raise ValueError("APOD is not a JPEG")
            f.seek(-2, 2)
            if f.read(2) != b"\xff\xd9":
                raise ValueError("Incomplete APOD JPEG")
        jpeg = jpegdec.JPEG(graphics)
        jpeg.open_file(FILENAME + ".new")
        jpeg.decode()
        del jpeg
        os.rename(FILENAME + ".new", FILENAME)
        apod_title = feed["title"]
        t = time.localtime(time.time() + TZ_OFFSET)
        last_updated = "%04d-%02d-%02d %02d:%02d" % (t[0], t[1], t[2], t[3], t[4])
        with open(METADATA, "w") as f:
            json.dump({"title": apod_title, "updated": last_updated}, f)
    except (OSError, ValueError, KeyError) as e:
        print("APOD update failed; keeping previous image:", e)
    finally:
        if socket is not None:
            socket.close()
        try:
            os.remove(FILENAME + ".new")
        except OSError:
            pass


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

