import requests, json
from datetime import datetime

url = "https://api.open-meteo.com/v1/forecast"

param = {
        "latitude": 30.076875686645508,
        "longitude": 31.200297474861145,
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


req = requests.get(url=url, params=param).json()

req["last_updated"] = datetime.now().isoformat(timespec="seconds")

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(req, f, indent=4, ensure_ascii=False)

