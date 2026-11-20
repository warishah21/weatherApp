import pandas as pd
import hopsworks
from dotenv import load_dotenv
from fetchapi import get_openweather_weather, get_openweather_airquality, get_aqicn_airquality, get_openmeteo
from feature import add_data_to_row, cleaning_data,adding_features
import os
load_dotenv()

Cols = ["hour","day","month","dayofaweek"]

def get_featurestore():
    project = hopsworks.login(api_key_value=os.getenv("API_KEY_HOPSWORKS"))
    return project.get_feature_store()


#raw:Fused row observation,one hour per row , features="Cleaned row with timestamp and derived features"
def get_featureGroup(feature_store):
    raw_features = feature_store.get_or_create_feature_group(name="raw_observations",version=1,primary_key=["timestamp"],event_time="timestamp",time_travel_format="HUDI")
    features = feature_store.get_or_create_feature_group(name="weather_features",version=1,primary_key=["timestamp"],event_time="timestamp",time_travel_format="HUDI")
    return raw_features,features

def type_fix(data):
    data = data.copy()
    for c in data.columns:
        if c == "timestamp":
            data[c] = pd.to_datetime(data[c],utc=True)
        elif c in Cols: 
            data[c] = pd.to_numeric(data[c], erros="coerce").astype("Int64")
        elif pd.api.types.is_bool_dtype(data[c]) or pd.api.types.is_datetime64_any_dtype(data[c]):
            continue
        else:
            try:
                data[c] = pd.to_numeric(data[c]).astype("float64")
            except (ValueError, TypeError):
                pass
    return data    

def match_database_schema(feature_group, data):
    data = type_fix(data)
    for f in feature_group.columns:
        if f.name in data.columns:
            if f.type == "timestamp":
                data[f.name] = pd.to_datetime(data[f.name], utc=True)
            elif f.type == "double":
                data[f.name] = pd.to_numeric(data[f.name], errors="coerce").astype("float64")
            elif f.type == "float":
                data[f.name] = pd.to_numeric(data[f.name], errors="coerce").astype("float32")
            elif f.type == "bigint":
                data[f.name] = pd.to_numeric(data[f.name], errors="coerce").astype("Int64")
            elif f.type == "int":
                data[f.name] = pd.to_numeric(data[f.name], errors="coerce").astype("Int32")
    return data


def run():
    feature_Store = get_featurestore()

    raw_Features, features = get_featureGroup(feature_Store)
    weather = get_openweather_weather()
    openweather_aq = get_openweather_airquality()
    aqicn_data = get_aqicn_airquality()
    openmeteo_data = get_openmeteo()

    data = pd.DataFrame([add_data_to_row(weather,openweather_aq,aqicn_data,openmeteo_data)])
    raw_Features.insert(match_database_schema(raw_Features,data), wait=True)

    try:
        history = raw_Features.read()
        history["timestamp"] = pd.to_datetime(history["timestamp"], utc=True)
        cutoff = pd.to_datetime(data["timestamp"].iloc[0], utc=True) - pd.Timedelta(hours=48)
        history = history[history["timestamp"] >= cutoff]
    except Exception:
        history = data
    df = adding_features(cleaning_data(history))
    features.insert(match_database_schema(features,df.tail(1).copy()), wait=True)


if __name__ == "__main__":
    run()


