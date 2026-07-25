import requests, json
from datetime import datetime
from config import LATITUDE, LONGITUDE 
from rich.console import Console

console = Console()


url = "https://api.open-meteo.com/v1/forecast"

param = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": [
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
            "is_day"
            ],
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "sunrise",
            "sunset",
            "uv_index_max"
            ],
        "current": [
            "temperature_2m", 
            "apparent_temperature", 
            "relative_humidity_2m", 
            "weather_code", 
            "wind_speed_10m", 
            "wind_direction_10m", 
            "is_day"
            ],
        "timezone": "Africa/Cairo",
        "forecast_days": 2,
    }



with console.status("[bold green]Progress...[/]"):
    try:
        response = requests.get(url=url, params=param, timeout=30)
        response.raise_for_status()
        
        req = response.json()
        req["last_updated"] = datetime.now().isoformat(timespec="seconds")
        
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(req, f, indent=4, ensure_ascii=False)
            
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
    except IOError as e:
        console.print(f"[red]Failed to write file: {e}[/]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/]")
