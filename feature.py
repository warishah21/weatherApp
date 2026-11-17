
import pandas as pd

#converting us and pm2.5 scale to an array(chi,ihi,ilo,cho) => (uppper PM2.5 concentration, lower aqi value, upper aqivalue, lower PM2,5 concentration)
breakpoints = [(9.0 , 0, 50, 0.0), (35.4, 51, 100,9.1), (55.4,101,150,35.5), (125.4,151,200,55.5), (225.4,201,300,125.4),(325.4,301,500,225.5)]

# calculates amount of the PM2.5 in the air and approximates it using US AQI scale
def calculate_airquality(PM2_5,upper_pm,lower_pm,loweraqi,higherqi):
    return ((higherqi-loweraqi)/(upper_pm-lower_pm)*(PM2_5-lower_pm)+loweraqi)

def convertingPM25(PM25):
    if PM25 is None:
        return None

    for upper_pm,upperaqi,loweraqi,lowerpm in breakpoints:
        if PM25<=upper_pm:
            return calculate_airquality(PM25,upper_pm,lowerpm,loweraqi,upperaqi)
    return 500

#combining the data from differnet platform to one to ssave it later
#getting air quality data from noth apis and fusing them
def get_aqicn_data(aqicn):
    try:
        return aqicn["data"]["aqi"]
    except (KeyError, TypeError,ValueError):
        return None


def get_PM25_ow_data(openweather_airquality):
    if openweather_airquality is None:
        return None
    return openweather_airquality["list"][0]["components"]["pm2_5"]

def choose_appropriate_aqi(aqi_of_aqicn,aqi_of_ow):
    if aqi_of_aqicn is not None:
        return aqi_of_aqicn
    return aqi_of_ow

def add_data_to_row(openweather_temp,openweather_aq,aciqn,openmeteo):
    PM25 = get_PM25_ow_data(openweather_aq)
    aqi_OPENWEATHER = convertingPM25(PM25)
    aciqn_aqi = get_aqicn_data(aciqn)
    fuse_aq = choose_appropriate_aqi(aciqn_aqi,aqi_OPENWEATHER)
    openMeteo = openmeteo or {}

    return{
        "timestamp": pd.Timestamp.now(tz="UTC").floor("h"),
        "weather": openweather_temp["main"]["temp"] if openweather_temp else None,
        "humidity": openweather_temp["main"]["humidity"] if openweather_temp else None,
        "wind_speed": openweather_temp["wind"]["speed"] if openweather_temp else None,
        "wind_degree": openweather_temp["wind"].get("deg")if openweather_temp else None,
        "precipitation": openweather_temp.get("rain", {}).get("1h",0.0)if openweather_temp else None,
        "rain_probability": openMeteo.get("rain_probab"),
        "uv_index": openMeteo.get("uv_index"),
        "openweather_aqi": aqi_OPENWEATHER,
        "aqicn_aqi": aciqn_aqi,
        "fused_aqi": fuse_aq 
    }
    
#handling the missing values - imputATION
def cleaning_data(data):
    data = data.sort_values("timestamp")
    data = data.drop_duplicates("timestamp",keep="last")
    #creates an hourly data
    data = data.set_index("timestamp").resample("1h").asfreq()
    data["is_missing"] = data.drop(columns=["openweather_aqi","aqicn_aqi"], errors="ignore").isna().any(axis=1)
    numerical_columns = data.select_dtypes("number").columns
    data[numerical_columns] = data[numerical_columns].ffill(limit=3)
    #filling the remainnnng col usingtypical value of the hour of the day
    data[numerical_columns] = data[numerical_columns].fillna(data.groupby(data.index.hour)[numerical_columns].transform("median"))
    return data.reset_index()

def adding_features(data):
    data = data.copy()
    data = data.sort_values(by="timestamp")

    #timbased faetures
    data["hour"] = data["timestamp"].dt.hour
    data["day"] = data["timestamp"].dt.day
    data["month"] = data["timestamp"].dt.month
    data["weekday"] = data["timestamp"].dt.weekday

    cols = ["weather","humidity","fused_aqi"]
    for c in cols:
        data[c + "_diff3"] = data[c] - data[c].shift(3)
        data[c + "_avg6"] = data[c].rolling(window=6,min_periods=1).mean()
        data[c +"_avg24"] = data[c].rolling(window=24, min_periods=1).mean()

    return data


