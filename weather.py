"""
Fetches a multi-day forecast from Open-Meteo (free, no API key needed)
and saves it to data.json for dashboard.py and notify.py to display.

Location resolution order:
    1. --city "Cairo"  (resolved through Open-Meteo's geocoding API)
    2. config.py with LATITUDE/LONGITUDE next to this script (gitignored)
    3. built-in default coordinates (Cairo), with a warning

The forecast is fetched with timezone=auto, so all times in data.json
are the local time of the resolved location, whatever it is.

Run:
    python weather.py                 # config.py / default location
    python weather.py --city "Cairo"  # any city name
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import requests
from rich.console import Console

console = Console()

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_FILE = SCRIPT_DIR / "data.json"
CONFIG_FILE = SCRIPT_DIR / "config.py"

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Used only when neither --city nor config.py is available.
LATITUDE_DEFAULT = 30.0444
LONGITUDE_DEFAULT = 31.2357

HOURLY_VARS = [
    "temperature_2m",
    "apparent_temperature",
    "weather_code",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_direction_180m",
    "precipitation_probability",
    "precipitation",
    "cloud_cover",
    "surface_pressure",
    "visibility",
    "is_day",
]

DAILY_VARS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "sunrise",
    "sunset",
    "uv_index_max",
    "precipitation_probability_max",
]

CURRENT_VARS = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
    "is_day",
]


def geocode_city(name):
    """Resolve a city name to (latitude, longitude, label) via Open-Meteo's
    free geocoding API. Returns None when nothing matches."""
    response = requests.get(
        GEOCODE_URL,
        params={"name": name, "count": 1, "language": "en", "format": "json"},
        timeout=30,
    )
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        return None
    place = results[0]
    label = ", ".join(
        part
        for part in (place.get("name"), place.get("admin1"), place.get("country"))
        if part
    )
    return place["latitude"], place["longitude"], label


def load_config_location():
    """Coordinates from config.py next to this script, if it exists."""
    if CONFIG_FILE.exists():
        from config import LATITUDE, LONGITUDE

        return LATITUDE, LONGITUDE, None
    return None


def resolve_location(city=None):
    """Pick the location to forecast: --city, config.py, or the default."""
    if city:
        geo = geocode_city(city)
        if geo is None:
            console.print(
                f"[yellow bold]No place found for '{city}'. Falling back to config/default coordinates.[/]"
            )
        else:
            return geo

    config_location = load_config_location()
    if config_location is not None:
        return config_location

    console.print(
        "[yellow bold]No --city given and no config.py found - using default coordinates (Cairo). "
        "Pass --city \"Your City\" or create config.py with LATITUDE/LONGITUDE.[/]"
    )
    return LATITUDE_DEFAULT, LONGITUDE_DEFAULT, None


def fetch_forecast(latitude, longitude, forecast_days=7, location_label=None):
    """Fetch the forecast and return the data dict, ready to save."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": HOURLY_VARS,
        "daily": DAILY_VARS,
        "current": CURRENT_VARS,
        "timezone": "auto",
        "forecast_days": forecast_days,
    }
    response = requests.get(url=FORECAST_URL, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    data["last_updated"] = datetime.now().isoformat(timespec="seconds")
    if location_label:
        data["location"] = location_label
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Fetch a weather forecast from Open-Meteo into data.json."
    )
    parser.add_argument(
        "--city",
        help="City name to forecast (e.g. --city 'Cairo'). "
        "Overrides config.py coordinates.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        choices=range(1, 17),
        metavar="1-16",
        help="Forecast days to fetch (default: 7).",
    )
    args = parser.parse_args(argv)

    try:
        with console.status("[bold green]Progress...[/]"):
            latitude, longitude, label = resolve_location(args.city)
            data = fetch_forecast(latitude, longitude, args.days, label)

            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

        where = data.get("location") or f"{latitude}, {longitude}"
        console.print(f"[bold green]󰄬 Done - {where}[/]")
        return True

    except requests.exceptions.Timeout:
        console.print("[red]Request timed out. Server didn't respond in time.[/]")
    except requests.exceptions.ConnectionError:
        console.print("[red]Failed to connect. Check your internet connection.[/]")
    except requests.exceptions.HTTPError as e:
        console.print(f"[red]HTTP Error: {e}[/]")
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Request failed: {e}[/]")
    except json.JSONDecodeError:
        console.print("[red]Received invalid JSON response.[/]")
    except OSError as e:
        console.print(f"[red]Failed to write file: {e}[/]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/]")
    return False


if __name__ == "__main__":
    main()
