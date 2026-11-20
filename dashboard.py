"""
Weather dashboard for Termux - reads data.json (produced by weather.py)
and prints a styled terminal report using the `rich` library.

weather.py only needs to run once a day (it fetches several days of
hourly + daily forecast). This script can be run any time - it always
finds the entry in the hourly arrays that matches the real current date
and hour, so the numbers stay accurate even without re-fetching.

Times in data.json are local to the forecast location (weather.py asks
Open-Meteo for timezone=auto). This script converts "now" into the
location's timezone, so the dashboard is correct even when you look up
a city in another timezone.

Setup:
    pip install rich

Run:
    python weather.py   # fetches fresh data.json (once a day is enough)
    python dashboard.py # displays it (safe to run any time)
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

COMMON_PATH = Path(__file__).resolve().parent
DATA_FILE = COMMON_PATH / "data.json"
WEATHER_FILE = COMMON_PATH / "weather.py"


# WMO weather_code -> (icon, description)
WEATHER_ICONS = {
    0: ("[yellow bold]󰖨[/]", "Clear sky"),
    1: ("[bold #C0EFFA][/]", "Mainly clear"),
    2: ("[bold #C0EFFA][/]", "Partly cloudy"),
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


def location_now(data):
    """Current date/time in the forecast location's timezone, as a naive
    datetime matching the timestamps stored in data.json."""
    tz_name = data.get("timezone")
    if tz_name:
        try:
            from zoneinfo import ZoneInfo

            return datetime.now(ZoneInfo(tz_name)).replace(tzinfo=None)
        except Exception:
            pass  # fall back to the UTC offset below
    offset = data.get("utc_offset_seconds")
    if offset is not None:
        return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            seconds=offset
        )
    return datetime.now()


def create_file():
    if not DATA_FILE.exists():
        try:
            subprocess.run(
                [sys.executable, WEATHER_FILE],
                cwd=COMMON_PATH,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False
    return True


def load_data(path=DATA_FILE):
    if create_file():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print("[red]❌ Failed to create data file[/]")
        return {}


def find_current_index(hourly, now=None):
    """Index in the hourly arrays matching the location's date + hour.

    Matches on the full "YYYY-MM-DDTHH:00" key rather than just the hour
    number, so it still finds the right slot even if weather.py hasn't
    re-run since midnight.
    """
    now = now or datetime.now()
    now_key = now.strftime("%Y-%m-%dT%H:00")
    times = hourly["time"]
    if now_key in times:
        return times.index(now_key)
    return max(0, len(times) - 1)  # fallback: last known entry


def current_from_hourly(data):
    """Build a 'current weather' snapshot from the hourly arrays at the
    index that matches right now, instead of the (possibly stale)
    top-level "current" field."""
    h = data["hourly"]
    i = find_current_index(h, location_now(data))
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
    chars = "".join(
        SPARK_BLOCKS[round((v - lo) / span * (len(SPARK_BLOCKS) - 1))]
        for v in values
    )
    return f"[#AFF233]{chars}[/]"


def bar(value, max_value, width=12, filled_char="█", empty_char="░"):
    """A simple horizontal gauge: value/max_value drawn as filled blocks."""
    ratio = max(0.0, min(1.0, value / max_value)) if max_value else 0.0
    filled = round(ratio * width)
    return f"[#AFF233]{filled_char * filled}[/]{empty_char * (width - filled)}"


def get_today_temps(data):
    """All hourly temperatures that belong to the location's calendar date."""
    h = data["hourly"]
    today_str = location_now(data).strftime("%Y-%m-%d")
    return [
        h["temperature_2m"][i]
        for i, t in enumerate(h["time"])
        if t.startswith(today_str)
    ]


def _to_minutes(hhmm):
    hh, mm = map(int, hhmm.split(":"))
    return hh * 60 + mm


def day_position_bar(data, width=24):
    """A 24-char bar with ↑ at sunrise, ↓ at sunset, 󰖨 / at right now."""
    d = data["daily"]
    sunrise_min = _to_minutes(d["sunrise"][0].split("T")[1])
    sunset_min = _to_minutes(d["sunset"][0].split("T")[1])
    now = location_now(data)
    now_min = now.hour * 60 + now.minute
    is_day = sunrise_min <= now_min < sunset_min
    now_icon = "[yellow bold]󰖨[/]" if is_day else "[bold #B5DEDF][/]"

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
    date_fetch = data["last_updated"].split("T")

    title = "[bold cyan][/]  Current Weather"
    if data.get("location"):
        title += f" - {data['location']}"

    body = (
        f"[{color}]{c['temperature_2m']}°C[/{color}]  {icon}  {desc}\n"
        f"Feels like: {c['apparent_temperature']}°C\n\n"
        f"[blue bold][/] Humidity  {humidity_bar}  {c['relative_humidity_2m']}%\n"
        f"[white bold][/]  Wind     {wind_bar}  {c['wind_speed_10m']} km/h"
    )
    return Panel(
        Align.left(body),
        title=title,
        subtitle=f"Data fetched: {' | '.join(date_fetch)}",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 4),
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
        "[green bold]󰄬 Safe[/]"
        if uv <= 5
        else "[yellow bold]󰀪 High[/]"
        if uv <= 10
        else "[red bold]󰚌 Extreme[/]"
    )

    body = (
        f"Max: [bold red]{d['temperature_2m_max'][0]}°C[/bold red]   "
        f"Min: [bold cyan]{d['temperature_2m_min'][0]}°C[/bold cyan]\n\n"
        f"Trend:  {spark}\n\n"
        f"{day_bar}\n"
        f"↑ {sunrise:<45}{sunset} ↓\n\n"
        f"[yellow bold]󱣖[/]  UV Index  {uv_bar}  {uv} {uv_level}"
    )
    return Panel(
        body,
        title="[bold magenta][/] Today",
        border_style="magenta",
        box=box.ROUNDED,
        padding=(1, 4),
    )


def hourly_table(data, hours_ahead=6):
    h = data["hourly"]
    start = find_current_index(h, location_now(data))
    end = min(start + hours_ahead, len(h["time"]))

    table = Table(
        title="[white]󱑆[/]  Next Hours",
        box=box.SIMPLE_HEAVY,
        highlight=True,
        expand=True,
    )
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


def forecast_table(data):
    """A row per forecast day: weekday, sky, min/max temps, rain chance, UV."""
    d = data["daily"]
    days = d.get("time") or []
    codes = d.get("weather_code") or []
    rain = d.get("precipitation_probability_max") or []
    uv = d.get("uv_index_max") or []

    table = Table(
        title="[white][/]  Next Days",
        box=box.SIMPLE_HEAVY,
        highlight=True,
        expand=True,
    )
    table.add_column("Day", style="bold")
    table.add_column("Sky", justify="center")
    table.add_column("Min", justify="center")
    table.add_column("Max", justify="center")
    table.add_column("Rain %", justify="center")
    table.add_column("UV", justify="center")

    for i, day in enumerate(days):
        date = datetime.strptime(day, "%Y-%m-%d")
        label = "Today" if i == 0 else date.strftime("%a %d %b")

        icon = "❓"
        if i < len(codes):
            icon, _ = get_icon(codes[i], is_day=1)

        t_min = d["temperature_2m_min"][i]
        t_max = d["temperature_2m_max"][i]
        rain_pct = f"{rain[i]}%" if i < len(rain) and rain[i] is not None else "-"
        uv_val = f"{uv[i]}" if i < len(uv) and uv[i] is not None else "-"

        table.add_row(
            label,
            icon,
            f"[{temp_color(t_min)}]{t_min}°C[/{temp_color(t_min)}]",
            f"[{temp_color(t_max)}]{t_max}°C[/{temp_color(t_max)}]",
            rain_pct,
            uv_val,
        )

    return table


def main():
    console = Console(record=True)
    data = load_data()
    if not data:
        console.print("[red]⚠️ No weather data available[/]")
        return

    console.print(current_panel(data))
    console.print(daily_panel(data))
    console.print(hourly_table(data))
    console.print(forecast_table(data))


if __name__ == "__main__":
    main()
