"""Hourly temperature line for Quincy, MA, adapted from pi-zero/weather-phat.py."""

import gc
import time
from urllib import urequest
from ujson import load

from inky_frame import BLACK, BLUE, RED, WHITE, YELLOW

LAT = 42.2529
LON = -71.0023
LOCATION_LABEL = "Quincy 02169"
NHOURS = 10
UPDATE_INTERVAL = 60
TZ_OFFSET = -4 * 3600

API_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=%s&longitude=%s&hourly=temperature_2m"
    "&temperature_unit=fahrenheit&timezone=auto&forecast_hours=%d"
) % (LAT, LON, NHOURS)

graphics = None
WIDTH = 600
HEIGHT = 448
times = []
temps = []
updated = ""
error = None


def update():
    global times, temps, updated, error
    error = None
    socket = None
    try:
        socket = urequest.urlopen(API_URL)
        data = load(socket)["hourly"]
        times = data["time"][:NHOURS]
        temps = data["temperature_2m"][:NHOURS]
        now = time.localtime(time.time() + TZ_OFFSET)
        hour = now[3] % 12 or 12
        updated = "upd %d:%02d%s" % (hour, now[4], "a" if now[3] < 12 else "p")
    except Exception as exc:
        print("Weather fetch failed:", exc)
        error = "No weather data"
    finally:
        if socket is not None:
            socket.close()
        gc.collect()


def _center(text, x, y, scale, pen):
    graphics.set_pen(pen)
    w = graphics.measure_text(text, scale)
    graphics.text(text, int(x - w // 2), int(y), WIDTH, scale)


def _hour_label(iso):
    try:
        hour = int(iso[11:13])
        return "%d%s" % (hour % 12 or 12, "a" if hour < 12 else "p")
    except Exception:
        return "--"


def draw():
    graphics.set_font("bitmap8")
    graphics.set_pen(WHITE)
    graphics.clear()

    if error or not temps:
        _center(error or "No weather data", WIDTH // 2, HEIGHT // 2 - 20, 4, BLACK)
        graphics.update()
        return

    margin = max(20, WIDTH // 30)
    graphics.set_pen(BLACK)
    graphics.text(LOCATION_LABEL, margin, 18, WIDTH, 3)
    if updated:
        w = graphics.measure_text(updated, 3)
        graphics.set_pen(RED)
        graphics.text(updated, WIDTH - margin - w, 18, WIDTH, 3)

    left, right = margin, WIDTH - margin
    top, bottom = 115, HEIGHT - 90
    count = len(temps)
    step = (right - left) / (count - 1) if count > 1 else 0
    xs = [left + i * step for i in range(count)] if count > 1 else [WIDTH // 2]
    low, high = min(temps), max(temps)
    span = high - low or 1
    ys = [bottom - (temp - low) * (bottom - top) / span for temp in temps]

    graphics.set_pen(YELLOW)
    for i in range(count - 1):
        graphics.line(int(xs[i]), int(ys[i]), int(xs[i + 1]), int(ys[i + 1]), 4)

    label_scale = 3 if WIDTH >= 600 else 2
    for i in range(count):
        x, y = int(xs[i]), int(ys[i])
        current = i == 0
        graphics.set_pen(RED if current else BLUE)
        radius = 7 if current else 5
        graphics.circle(x, y, radius)
        _center("%d" % round(temps[i]), x, y - 35, label_scale,
                RED if current else BLACK)
        _center(_hour_label(times[i]), x, HEIGHT - 55, 2, BLACK)

    graphics.update()
    gc.collect()
