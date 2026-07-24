"""
Weather dashboard for Termux - reads data.json (produced by weather.py)
and prints a styled terminal report using the `rich` library.

weather.py only needs to run once a day (it fetches the whole day's
hourly forecast). This script can be run any time - it always finds
the entry in the hourly arrays that matches the real current date and
hour, so the numbers stay accurate even without re-fetching.

Setup:
    pip install rich

Run:
    python weather.py   # fetches fresh data.json (once a day is enough)
    python dashboard.py # displays it (safe to run any time)
"""

import json
import os
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich import box

# Path is relative to this script's own location, not to the folder
# you happen to be standing in when it gets launched.
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")

# WMO weather_code -> (icon, description)
WEATHER_ICONS = {
    0: ("[yellow bold]󰖨[/]", "Clear sky"),
    1: ("[blue bold][/]", "Mainly clear"),
    2: ("[blue bold][/]", "Partly cloudy"),
    3: ("[white bold]󰖐[/]", "Overcast"),
    45: ("[grey62 bold]󰖑[/]", "Fog"),
    48: ("[grey62 bold]󰖑[/]", "Rime fog"),
    51: ("[blue]󰖗[/]", "Light drizzle"),
    53: ("[blue bold]󰖗[/]", "Moderate drizzle"),
    55: ("[blue bold]󰖖[/]", "Dense drizzle"),
    61: ("[blue]󰖗[/]", "Slight rain"),
    63: ("[blue bold]󰖖[/]", "Moderate rain"),
    65: ("[bold dodger_blue2]󰖖[/]", "Heavy rain"),
    71: ("[cyan]󰖘[/]", "Slight snow"),
    73: ("[cyan bold]󰖘[/]", "Moderate snow"),
    75: ("[bold white]󰖘[/]", "Heavy snow"),
    80: ("[blue]󰖗[/]", "Slight rain showers"),
    81: ("[blue bold]󰖖[/]", "Moderate rain showers"),
    82: ("[bold dodger_blue2]󰖖[/]", "Violent rain showers"),
    95: ("[yellow bold]󰖓[/]", "Thunderstorm"),
    96: ("[bold magenta]󰖒[/]", "Thunderstorm + hail"),
    99: ("[bold red]󰖓[/]", "Severe thunderstorm"),
}

# Clear/cloudy codes get a moon instead of a sun at night.
NIGHT_OVERRIDE = {0: "[blue bold][/]", 1: "[blue bold][/]"}


SPARK_BLOCKS = "▁▂▃▄▅▆▇█"


def get_icon(code, is_day=1):
    icon, desc = WEATHER_ICONS.get(code, ("❓", "Unknown"))
    if is_day == 0 and code in NIGHT_OVERRIDE:
        icon = NIGHT_OVERRIDE[code]
    return icon, desc


def temp_color(temp):
    if temp >= 38:
        return "bold red"
    if temp >= 30:
        return "bold dark_orange"
    if temp >= 20:
        return "bold yellow"
    return "bold cyan"


def load_data(path=DATA_FILE):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_current_index(hourly):
    """Index in the hourly arrays matching today's date + current hour.

    Matches on the full "YYYY-MM-DDTHH:00" key rather than just the hour
    number, so it still finds the right slot even if weather.py hasn't
    re-run since midnight (the array holds 2 days once forecast_days=2).
    """
    now_key = datetime.now().strftime("%Y-%m-%dT%H:00")
    times = hourly["time"]
    if now_key in times:
        return times.index(now_key)
    return max(0, len(times) - 1)  # fallback: last known entry


def current_from_hourly(data):
    """Build a 'current weather' snapshot from the hourly arrays at the
    index that matches right now, instead of the (possibly stale)
    top-level "current" field."""
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


def sparkline(values):
    """Turn a list of numbers into a one-line unicode bar graph."""
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if hi == lo:
        return SPARK_BLOCKS[0] * len(values)
    span = hi - lo
    return "".join(
        SPARK_BLOCKS[round((v - lo) / span * (len(SPARK_BLOCKS) - 1))]
        for v in values
    )


def bar(value, max_value, width=12, filled_char="█", empty_char="░"):
    """A simple horizontal gauge: value/max_value drawn as filled blocks."""
    ratio = max(0.0, min(1.0, value / max_value)) if max_value else 0.0
    filled = round(ratio * width)
    return f"[green]{filled_char * filled}[/]{empty_char * (width - filled)}"

def get_today_temps(data):
    """All hourly temperatures that belong to today's calendar date."""
    h = data["hourly"]
    today_str = datetime.now().strftime("%Y-%m-%d")
    return [
        h["temperature_2m"][i]
        for i, t in enumerate(h["time"])
        if t.startswith(today_str)
    ]


def _to_minutes(hhmm):
    hh, mm = map(int, hhmm.split(":"))
    return hh * 60 + mm


def day_position_bar(data, width=24):
    """A 24-char bar with ↑ at sunrise, ↓ at sunset, ● at right now."""
    d = data["daily"]
    sunrise_min = _to_minutes(d["sunrise"][0].split("T")[1])
    sunset_min = _to_minutes(d["sunset"][0].split("T")[1])
    now = datetime.now()
    now_min = now.hour * 60 + now.minute
    is_day = sunrise_min <= now_min < sunset_min
    now_icon = "[yellow bold][/]" if is_day else "[blue bold][/]"

    def pos(m):
        return min(width - 1, max(0, round(m / (24 * 60) * (width - 1))))

    chars = ["[bold]─[/]"] * width
    chars[pos(sunrise_min)] = "[bold]↑[/]"
    chars[pos(sunset_min)] = "[bold]↓[/]"
    chars[pos(now_min)] = now_icon  # drawn last so "now" always wins ties
    return "".join(chars)


def current_panel(data):
    c = current_from_hourly(data)
    icon, desc = get_icon(c["weather_code"], c["is_day"])
    color = temp_color(c["temperature_2m"])

    humidity_bar = bar(c["relative_humidity_2m"], 100)
    wind_bar = bar(c["wind_speed_10m"], 60)

    body = (
        f"[{color}]{c['temperature_2m']}°C[/{color}]  {icon}  {desc}\n"
        f"Feels like: {c['apparent_temperature']}°C\n\n"
        f"[blue bold][/] Humidity  {humidity_bar}  {c['relative_humidity_2m']}%\n"
        f"[white bold][/]  Wind      {wind_bar}  {c['wind_speed_10m']} km/h"
    )
    return Panel(
        Align.left(body),
        title="[blue bold][/]  Current Weather",
        subtitle=f"Data fetched: {data.get('last_updated', '—')}",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(0, 4)
    )


def daily_panel(data):
    d = data["daily"]
    sunrise = d["sunrise"][0].split("T")[1]
    sunset = d["sunset"][0].split("T")[1]
    uv = d["uv_index_max"][0]

    spark = sparkline(get_today_temps(data))
    uv_bar = bar(uv, 12)
    day_bar = day_position_bar(data)
    uv_level = (
        "[green bold]󰄬 Safe[/]" if uv <= 5 else
        "[yellow bold]󰀪 High[/]" if uv <= 10 else
        "[red bold]󰚌 Extreme[/]"
    )

    body = (
        f"Max: [bold red]{d['temperature_2m_max'][0]}°C[/bold red]   "
        f"Min: [bold cyan]{d['temperature_2m_min'][0]}°C[/bold cyan]\n"
        f"Trend:  {spark}\n\n"
        f"{day_bar}\n"
        f"↑ {sunrise:<45}{sunset} ↓\n\n"
        f"[yellow bold]󱣖[/]  UV Index  {uv_bar}  {uv} {uv_level}"
    )
    return Panel(body, title="[blue bold][/] Today", border_style="magenta", box=box.ROUNDED, padding=(0, 4))


def hourly_table(data, hours_ahead=8):
    h = data["hourly"]
    start = find_current_index(h)
    end = min(start + hours_ahead, len(h["time"]))

    table = Table(title="[white]󱑆[/]  Next Hours", box=box.SIMPLE_HEAVY, highlight=True, expand=True)
    table.add_column("Time", style="bold")
    table.add_column("Temp", justify="center")
    table.add_column("Sky", justify="center")
    table.add_column("Rain %", justify="center")

    for i in range(start, end):
        time_label = h["time"][i].split("T")[1]
        temp = h["temperature_2m"][i]
        icon, _ = get_icon(h["weather_code"][i], h["is_day"][i])
        rain = h["precipitation_probability"][i]
        color = temp_color(temp)
        table.add_row(time_label, f"[{color}]{temp}°C[/{color}]", icon, f"{rain}%")

    return table


def main():
    console = Console(record=True)
    data = load_data()

    console.print(current_panel(data))
    console.print(daily_panel(data))
    console.print(hourly_table(data))


if __name__ == "__main__":
    main()
