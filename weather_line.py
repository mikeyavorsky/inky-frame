"""Hourly temperature line for Quincy, MA, adapted from pi-zero/weather-phat.py."""

import gc
import time
from urllib import urequest
from ujson import load

from inky_frame import BLACK, BLUE, RED, WHITE, YELLOW

LAT = 42.2529
LON = -71.0023
NHOURS = 24
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
        forecast_times = data["time"][:NHOURS]
        forecast_temps = data["temperature_2m"][:NHOURS]
        # Open-Meteo starts at the current local hour. Only retain readings
        # from that date, so the extrema are for the rest of today rather
        # than the next 24 hours.
        today = forecast_times[0][:10]
        times = []
        temps = []
        for forecast_time, forecast_temp in zip(forecast_times, forecast_temps):
            if forecast_time[:10] != today:
                break
            times.append(forecast_time)
            temps.append(forecast_temp)
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


def _bold_text(text, x, y, scale, pen):
    """Draw bitmap text with a small offset to give it a heavier weight."""
    graphics.set_pen(pen)
    graphics.text(text, int(x), int(y), WIDTH, scale)
    graphics.text(text, int(x + 2), int(y), WIDTH, scale)
    graphics.text(text, int(x), int(y + 2), WIDTH, scale)
    graphics.text(text, int(x + 2), int(y + 2), WIDTH, scale)


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
    low, high = min(temps), max(temps)

    # The remaining-day extrema are deliberately oversized and right aligned.
    # Draw them before the graph: its white under-stroke cuts a clean channel
    # through a digit wherever the two overlap.
    number_scale = 14 if WIDTH >= 600 else 10
    high_text = "%d" % round(high)
    low_text = "%d" % round(low)
    high_x = WIDTH - margin - graphics.measure_text(high_text, number_scale) - 2
    low_x = WIDTH - margin - graphics.measure_text(low_text, number_scale) - 2
    _bold_text(high_text, high_x, 8, number_scale, BLACK)
    _bold_text(low_text, low_x,
               HEIGHT - (number_scale * 8) - 10, number_scale, BLACK)

    left, right = margin, WIDTH - margin
    top, bottom = 55, HEIGHT - 55
    count = len(temps)
    step = (right - left) / (count - 1) if count > 1 else 0
    xs = [left + i * step for i in range(count)] if count > 1 else [WIDTH // 2]
    span = high - low or 1
    ys = [bottom - (temp - low) * (bottom - top) / span for temp in temps]

    # A broad white line erases the portion of a high/low digit behind the
    # forecast, then the narrower yellow stroke remains legible in the gap.
    for pen, thickness in ((WHITE, 12), (YELLOW, 4)):
        graphics.set_pen(pen)
        for i in range(count - 1):
            graphics.line(int(xs[i]), int(ys[i]),
                          int(xs[i + 1]), int(ys[i + 1]), thickness)

    label_scale = 3 if WIDTH >= 600 else 2
    for i in range(count):
        x, y = int(xs[i]), int(ys[i])
        current = i == 0
        graphics.set_pen(RED if current else BLUE)
        graphics.circle(x, y, 7 if current else 5)
        _center("%d" % round(temps[i]), x, y - 35, label_scale,
                RED if current else BLACK)
        _center(_hour_label(times[i]), x, HEIGHT - 45, 2, BLACK)

    graphics.update()
    gc.collect()
