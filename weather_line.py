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
    "&daily=temperature_2m_max,temperature_2m_min&forecast_days=2"
    "&temperature_unit=fahrenheit&timezone=auto&forecast_hours=%d"
) % (LAT, LON, NHOURS)

graphics = None
WIDTH = 600
HEIGHT = 448
times = []
temps = []
precip_chances = []
daily_dates = []
daily_highs = []
daily_lows = []
updated = ""
error = None


def update():
    global times, temps, precip_chances
    global daily_dates, daily_highs, daily_lows, updated, error
    error = None
    socket = None
    try:
        socket = urequest.urlopen(API_URL)
        data = load(socket)
        hourly = data["hourly"]
        daily = data.get("daily", {})
        times = hourly["time"][:NHOURS]
        temps = hourly["temperature_2m"][:NHOURS]
        precip_chances = hourly["precipitation_probability"][:NHOURS]
        daily_dates = daily.get("time", [])
        daily_highs = daily.get("temperature_2m_max", [])
        daily_lows = daily.get("temperature_2m_min", [])
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


def _day_extrema(date, count):
    for i in range(min(len(daily_dates), len(daily_highs), len(daily_lows))):
        if daily_dates[i] == date:
            return daily_lows[i], daily_highs[i]

    # Keep drawing useful data if a response ever omits the daily block.
    day_temps = [
        temps[i] for i in range(count)
        if times[i][:10] == date
    ]
    if day_temps:
        return min(day_temps), max(day_temps)
    return None


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

    if error or not times or not temps or not precip_chances:
        _center(error or "No weather data", WIDTH // 2, HEIGHT // 2 - 20, 4, BLACK)
        graphics.update()
        return

    count = min(len(times), len(temps), len(precip_chances), NHOURS)
    chart_temps = temps[:count]
    margin = max(20, WIDTH // 30)
    low, high = min(chart_temps), max(chart_temps)
    left, right = margin, WIDTH - margin
    top, bottom = 30, HEIGHT - 75
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

    # Today's daily high/low anchors the left edge. If the hourly window
    # crosses midnight, the next day's pair anchors the right edge.
    first_date = times[0][:10]
    second_date = None
    for i in range(1, count):
        if times[i][:10] != first_date:
            second_date = times[i][:10]
            break

    number_scale = 14 if WIDTH >= 600 else 10
    high_y = 8
    low_y = HEIGHT - number_scale * 8 - 10
    first_extrema = _day_extrema(first_date, count)
    if first_extrema:
        day_low, day_high = first_extrema
        _bold_text("%d" % round(day_high), margin, high_y,
                   number_scale, BLACK)
        _bold_text("%d" % round(day_low), margin, low_y,
                   number_scale, BLACK)

    if second_date:
        second_extrema = _day_extrema(second_date, count)
        if second_extrema:
            day_low, day_high = second_extrema
            high_text = "%d" % round(day_high)
            low_text = "%d" % round(day_low)
            high_x = WIDTH - margin - graphics.measure_text(
                high_text, number_scale
            ) - 2
            low_x = WIDTH - margin - graphics.measure_text(
                low_text, number_scale
            ) - 2
            _bold_text(high_text, high_x, high_y, number_scale, BLACK)
            _bold_text(low_text, low_x, low_y, number_scale, BLACK)

    # Precipitation always uses a fixed, unlabeled 0–100% vertical scale.
    precip_ys = [
        bottom - max(0, min(100, chance)) * (bottom - top) / 100
        for chance in precip_chances[:count]
    ]
    # The white under-stroke keeps the curve legible through a large digit.
    for pen, thickness in ((WHITE, 12), (BLUE, 4)):
        graphics.set_pen(pen)
        for i in range(count - 1):
            graphics.line(int(xs[i]), int(precip_ys[i]),
                          int(xs[i + 1]), int(precip_ys[i + 1]), thickness)

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
