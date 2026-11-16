import os , requests
from datetime import datetime, timezone
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

def main():
    openweather_weather = get_openweather_weather()
    openweather_aq = get_openweather_airquality()
    aqicn = get_aqicn_airquality()
    
    weather = openweather_weather["main"]["temp"]
    humidity = openweather_weather["main"]["humidity"]
    openweather_aqi = openweather_aq["list"][0]["main"]["aqi"]
    aqi_status = aqicn["data"]["aqi"]

    print(datetime.now(timezone.utc))
    
    print(city_name.title())
    print("Temperature:", weather, "°C")
    print("Humidity:", humidity, "%")
    print("OpenWeather Air Quality Index:", openweather_aqi)
    print("AQICN Air Quality Index:", aqi_status)


if __name__ == "__main__":
    main()
    
