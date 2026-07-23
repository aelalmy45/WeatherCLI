"""
Sends an Android notification with the current weather, using
Termux:API's `termux-notification` command.

weather.py only needs to run once a day (it fetches the whole day's
hourly forecast). This script can safely run every hour on its own -
it finds the entry in the hourly arrays matching the real current
date and hour, so the numbers stay accurate without re-fetching.

Requirements:
    pkg install termux-api
    (and install the "Termux:API" app from F-Droid on your phone)

Run:
    python weather.py   # fetches fresh data.json (once a day is enough)
    python notify.py    # sends the notification (safe to run hourly)
"""

import json
import os
import subprocess
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")

WEATHER_ICONS = {
    0: ("☀️", "Clear sky"),
    1: ("🌤️", "Mainly clear"),
    2: ("⛅", "Partly cloudy"),
    3: ("☁️", "Overcast"),
    45: ("🌫️", "Fog"),
    48: ("🌫️", "Rime fog"),
    51: ("🌦️", "Light drizzle"),
    53: ("🌦️", "Moderate drizzle"),
    55: ("🌧️", "Dense drizzle"),
    61: ("🌧️", "Slight rain"),
    63: ("🌧️", "Moderate rain"),
    65: ("🌧️", "Heavy rain"),
    71: ("🌨️", "Slight snow"),
    73: ("🌨️", "Moderate snow"),
    75: ("❄️", "Heavy snow"),
    80: ("🌦️", "Slight rain showers"),
    81: ("🌧️", "Moderate rain showers"),
    82: ("⛈️", "Violent rain showers"),
    95: ("⛈️", "Thunderstorm"),
    96: ("⛈️", "Thunderstorm + hail"),
    99: ("⛈️", "Severe thunderstorm"),
}

NIGHT_OVERRIDE = {0: "🌙", 1: "🌙", 2: "☁️", 3: "☁️"}


def get_icon(code, is_day=1):
    icon, desc = WEATHER_ICONS.get(code, ("❓", "Unknown"))
    if is_day == 0 and code in NIGHT_OVERRIDE:
        icon = NIGHT_OVERRIDE[code]
    return icon, desc


def load_data(path=DATA_FILE):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_current_index(hourly):
    now_key = datetime.now().strftime("%Y-%m-%dT%H:00")
    times = hourly["time"]
    if now_key in times:
        return times.index(now_key)
    return max(0, len(times) - 1)


def current_from_hourly(data):
    h = data["hourly"]
    i = find_current_index(h)
    return {
        "temperature_2m": h["temperature_2m"][i],
        "apparent_temperature": h["apparent_temperature"][i],
        "relative_humidity_2m": h["relative_humidity_2m"][i],
        "weather_code": h["weather_code"][i],
        "wind_speed_10m": h["wind_speed_10m"][i],
        "is_day": h["is_day"][i],
    }


def send_notification(data):
    c = current_from_hourly(data)
    icon, desc = get_icon(c["weather_code"], c["is_day"])

    title = f"{icon} {c['temperature_2m']}°C - {desc}"
    content = (
        f"Feels like {c['apparent_temperature']}°C  |  "
        f"Humidity {c['relative_humidity_2m']}%  |  "
        f"Wind {c['wind_speed_10m']} km/h"
    )

    subprocess.run(
        [
            "termux-notification",
            "--title", title,
            "--content", content,
            "--id", "weather_hourly",
            "--priority", "low",
        ],
        check=True,
    )


if __name__ == "__main__":
    weather_data = load_data()
    send_notification(weather_data)

