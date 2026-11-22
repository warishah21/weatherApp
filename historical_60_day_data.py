import os
from dotenv import load_dotenv
import requests
import time
import hopsworks
from feature import convertingPM25,cleaning_data,adding_features
import pandas as pd

load_dotenv()
HOP_KEY = os.getenv("API_KEY_HOPSWORKS")
OPEN_WEATHER_KEY = os.getenv("OPEN_WEATHER_API")
Latitude = 24.8608
Longitude = 67.0104

def get_data(url, params, retries=3):
    for attempt in range(retries):
        response = requests.get(url,params=params,timeout=60,headers={"Accept-Encoding": "identity"})

        if response.status_code == 429 and attempt < retries - 1:
            time.sleep(10 * (attempt + 1))
            continue

        response.raise_for_status()

        if not response.content.strip():

            if attempt < retries - 1:
                time.sleep(5)
                continue

            raise ValueError("Open-Meteo returned an empty response")

        return response.json()

    raise Exception("Request failed")

#fetch historical weather data form openmeteo
def weatherBackfill():
    parameters = {"latitude": Latitude, "longitude":Longitude, "past_days": 30, "forecast_days":1, "timezone":"UTC", "wind_speed_unit":"ms", "hourly": ",".join(["temperature_2m", "relative_humidity_2m","wind_speed_10m","wind_direction_10m", "precipitation", "uv_index", "precipitation_probability"])}
    json_response = get_data("https://api.open-meteo.com/v1/forecast",parameters)
    hourly = json_response.get("hourly",{})
    weather_Data = {        
        "timestamp": pd.to_datetime(hourly["time"], utc=True),
        "temp": hourly["temperature_2m"],
        "humidity": hourly["relative_humidity_2m"],
        "wind_speed": hourly["wind_speed_10m"],
        "wind_deg": hourly["wind_direction_10m"],
        "precip_mm": hourly["precipitation"],
        "rain_prob": hourly["precipitation_probability"],
        "uv_index": hourly["uv_index"]
    }
    return pd.DataFrame(weather_Data)

#fetch historical air quality data
def airQualityBackfill(end):
    start = end - pd.Timedelta(days = 60)
    rows = []
    while start < end: 
        stop = min(start + pd.Timedelta(days = 15), end)
        parameters = {"lat":Latitude, "lon": Longitude,"appid": OPEN_WEATHER_KEY,"start": int(start.timestamp()), "end":int(stop.timestamp())}
        json_response = get_data("https://api.openweathermap.org/data/2.5/air_pollution/history",parameters)
        records = json_response.get("list",[])
        for record in records:
            timestamp = pd.to_datetime(record["dt"],unit="s",utc=True)
            pm25 = record["components"]["pm2_5"]
            air_quality = convertingPM25(pm25)

            rows.append({"timestamp":timestamp,"aqi_ow":air_quality})
        start = stop
    data = pd.DataFrame(rows)
    return data.drop_duplicates(subset="timestamp")

TargetColumns = ["aqi_fused", "temp", "precip_mm", "rain_prob","humidity", "uv_index", "wind_speed", "wind_deg"]

def add_Targets(data, horizon=24):
    data = data.sort_values(by="timestamp").copy()
    target = {}
    for col in TargetColumns:
        target["target_"+col] = data[col].shift(-horizon)
    data = pd.concat([data,pd.DataFrame(target, index=data.index)],axis=1)
    return data

def building_history():
    end = pd.Timestamp.now(tz="UTC").floor("h")
    weatherData = weatherBackfill()
    airQuality_data = airQualityBackfill(end)
    merged_data = pd.merge(weatherData,airQuality_data,on="timestamp",how="left")
    merged_data = merged_data[merged_data["timestamp"] <= end].copy()
    merged_data["aqi_aqicn"] = float("nan")
    merged_data["aqi_fused"] = merged_data["aqi_ow"]
    rain_missing_data = merged_data["rain_prob"].isna()
    merged_data.loc[rain_missing_data, "rain_prob"] = ((merged_data.loc[rain_missing_data, "precip_mm"] > 0).astype(float) * 100)
    for cols in merged_data.columns:
        if cols != "timestamp":
            merged_data[cols] = merged_data[cols].astype("float64")
    merged_data = cleaning_data(merged_data)
    merged_data["weather"] = merged_data["temp"]
    merged_data["fused_aqi"] = merged_data["aqi_fused"]
    merged_data = adding_features(merged_data)

    merged_data = merged_data.drop(
        columns=["weather", "fused_aqi"]
    )

    merged_data["hour"] = merged_data["hour"].astype("int64")
    merged_data["day"] = merged_data["day"].astype("int64")
    merged_data["month"] = merged_data["month"].astype("int64")
    merged_data["weekday"] = merged_data["weekday"].astype("float64")

    return merged_data

if __name__ == "__main__":

    history = building_history()
    print(history.shape, history["timestamp"].min(), "->", history["timestamp"].max())
    print("targets available:", int(add_Targets(history)["target_temp"].notna().sum()))
    project = hopsworks.login(api_key_value=HOP_KEY)
    featureStore = project.get_feature_store()
    raw_features = featureStore.get_or_create_feature_group(name="raw_observations", version=1,primary_key=["timestamp"], event_time="timestamp")
    feat_fg = featureStore.get_or_create_feature_group(name="weather_features", version=1,primary_key=["timestamp"], event_time="timestamp")
    raw_cols = ["timestamp", "temp", "humidity", "wind_speed", "wind_deg", "precip_mm","rain_prob", "uv_index", "aqi_ow", "aqi_aqicn", "aqi_fused"]
    RENAME = {"temp": "weather", "precip_mm": "precipitation", "rain_prob": "rain_probability","aqi_ow": "openweather_aqi", "aqi_aqicn": "aqicn_aqi", "aqi_fused": "fused_aqi","wind_deg": "wind_degree"}

    raw_out = history[raw_cols].rename(columns=RENAME)
    feat_out = history.rename(columns=RENAME)
    bad = False
    for fg, d in [(raw_features, raw_out), (feat_fg, feat_out)]:
        exp = [f.name for f in fg.features]
        missing = [c for c in exp if c not in d.columns]
        extra = [c for c in d.columns if c not in exp]
        print(fg.name, "| missing:", missing, "| extra:", extra)
        bad = bad or bool(missing or extra)
    if bad:
        raise SystemExit("Column names still don't match, fix RENAME first.")
    
    raw_features.insert(raw_out)
    feat_fg.insert(feat_out)
    print("Backfill written.")