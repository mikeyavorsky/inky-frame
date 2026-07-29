"""Twelve-hour temperature and precipitation forecast for Quincy, MA."""

import gc
import time
from urllib import urequest
from ujson import load

from inky_frame import BLACK, BLUE, RED, WHITE

LAT = 42.2529
LON = -71.0023
NHOURS = 12
UPDATE_INTERVAL = 60
TZ_OFFSET = -4 * 3600

API_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=%s&longitude=%s"
    "&hourly=temperature_2m,precipitation_probability"
    "&temperature_unit=fahrenheit&timezone=auto&forecast_hours=%d"
) % (LAT, LON, NHOURS)

graphics = None
WIDTH = 600
HEIGHT = 448
times = []
temps = []
precip_chances = []
updated = ""
error = None


def update():
    global times, temps, precip_chances, updated, error
    error = None
    socket = None
    try:
        socket = urequest.urlopen(API_URL)
        data = load(socket)["hourly"]
        times = data["time"][:NHOURS]
        temps = data["temperature_2m"][:NHOURS]
        precip_chances = data["precipitation_probability"][:NHOURS]
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

    if error or not temps or not precip_chances:
        _center(error or "No weather data", WIDTH // 2, HEIGHT // 2 - 20, 4, BLACK)
        graphics.update()
        return

    margin = max(20, WIDTH // 30)
    low, high = min(temps), max(temps)
    left, right = margin, WIDTH - margin
    top, bottom = 30, HEIGHT - 75
    count = min(len(times), len(temps), len(precip_chances), NHOURS)
    step = (right - left) / (count - 1) if count > 1 else 0
    xs = [left + i * step for i in range(count)] if count > 1 else [WIDTH // 2]
    temp_span = high - low
    if temp_span:
        temp_ys = [
            bottom - (temp - low) * (bottom - top) / temp_span
            for temp in temps[:count]
        ]
    else:
        temp_ys = [(top + bottom) / 2 for _ in range(count)]

    # Precipitation always uses a fixed, unlabeled 0–100% vertical scale.
    precip_ys = [
        bottom - max(0, min(100, chance)) * (bottom - top) / 100
        for chance in precip_chances[:count]
    ]
    graphics.set_pen(BLUE)
    for i in range(count - 1):
        graphics.line(int(xs[i]), int(precip_ys[i]),
                      int(xs[i + 1]), int(precip_ys[i + 1]), 4)

    label_scale = 3 if WIDTH >= 600 else 2
    for i in range(count):
        x, y = int(xs[i]), int(temp_ys[i])
        # The hourly values themselves imply the temperature curve; there is
        # deliberately no connecting line or point marker for this series.
        _center("%d" % round(temps[i]), x, y - label_scale * 4,
                label_scale, RED)
        _center(_hour_label(times[i]), x, HEIGHT - 45, 2, BLACK)

    graphics.update()
    gc.collect()
