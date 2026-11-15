import streamlit as st
import hopsworks

api_key = st.secrets["API_KEY_HOPSWORKS"]
project = hopsworks.login(api_key_value=os.environ["API_KEY_HOPSWORKS"])
st.title("WeatherApp")
st.write("Hello World")