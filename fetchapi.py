import http
import os , requests
from datetime import datetime, timezone
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

AQICN_KEY = os.getenv("AQICN_KEY")
OPENWEATHER_KEY = os.getenv("OPEN_WEATHER_API")
latitude = 24.8608
longitude = 67.0104
city_name = "karachi"

def get_data(url, params):
    response = requests.get(url, params, timeout=15)
    response.raise_for_status()
    return response.json()
def get_openweather_weather():
    api_link = "https://api.openweathermap.org/data/2.5/weather"
    parameter = {"lat": latitude, "lon": longitude, "appid": OPENWEATHER_KEY, "units" : "metric"}
    return get_data(api_link, parameter)
def get_openweather_airquality():
    api_link = "https://api.openweathermap.org/data/2.5/air_pollution"
    parameter = {"lat": latitude,"lon":longitude,"appid":OPENWEATHER_KEY}
    return get_data(api_link,parameter)

def get_aqicn_airquality():
    api_link = f"https://api.waqi.info/feed/{city_name}/"
    result = get_data(api_link, {"token":AQICN_KEY})
    if result.get("status") != "ok":
        raise ValueError("AQICN data not reachable")
    return result

def get_openmeteo():
    """Third source: UV index and rain Probabliilty for current time."""
    api_link = "https://api.open-meteo.com/v1/forecast"
    parameter = {"latitude": latitude, "longitude":longitude, "hourly": "uv_index,precipitation_probability", "forecast_days": 1,"timezone":"UTC"}
    data = get_data(api_link,parameter)
    hourly = data["hourly"]
    now = pd.Timestamp.now(tz="UTC").floor("h").strftime("%Y-%m-%dT%H:00")
    index = hourly["time"].index(now)
    return {"uv_index": hourly["uv_index"][index], "rain_probab": hourly["precipitation_probability"][index]}


