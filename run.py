import pandas as pd
from fetchapi import (get_openweather_weather,get_openweather_airquality, get_aqicn_airquality, get_openmeteo)
from feature import add_data_to_row, cleaning_data, adding_features

weather = get_openweather_weather()
pollution = get_openweather_airquality()
aqicn = get_aqicn_airquality()
meteo = get_openmeteo()

row = add_data_to_row(weather, pollution, aqicn, meteo)
df = adding_features(cleaning_data(pd.DataFrame([row])))
pd.set_option("display.max_columns", None)
print(df.T)