import pandas as pd
import hopsworks
from dotenv import load_dotenv
from fetchapi import get_openweather_weather, get_openweather_airquality, get_aqicn_airquality, get_openmeteo
from feature import add_data_to_row, cleaning_data,adding_features
import os
load_dotenv()

def get_featurestore():
    project = hopsworks.login(api_key_value=os.getenv("API_KEY_HOPSWORKS"))
    return project.get_feature_store()


#raw:Fused row observation,one hour per row , features="Cleaned row with timestamp and derived features"
def get_featureGroup(feature_store):
    raw_features = feature_store.get_or_create_feature_group(name="raw_observations",version=1,primary_key=["timestamp"],event_time="timestamp",time_travel_format="HUDI")
    features = feature_store.get_or_create_feature_group(name="weather_features",version=1,primary_key=["timestamp"],event_time="timestamp",time_travel_format="HUDI")
    return raw_features,features

def run():
    feature_Store = get_featurestore()
    raw_Features, features = get_featureGroup(feature_Store)
    weather = get_openweather_weather()
    openweather_aq = get_openweather_airquality()
    aqicn_data = get_aqicn_airquality()
    openmeteo_data = get_openmeteo()

    data = pd.DataFrame([add_data_to_row(weather,openweather_aq,aqicn_data,openmeteo_data)])
    raw_Features.insert(data, wait=True)

    try:
        history = raw_Features.read()
        history = history[history["timestamp"]>=data["timestamp"].iloc[0]-pd.Timedelta(hours=48)]
    except Exception:
        history = data
    df = adding_features(cleaning_data(history))
    features.insert(df.tail(1))

if __name__ == "__main__":
    run()


