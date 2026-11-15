import hopsworks
import os
from dotenv import load_dotenv

load_dotenv()

project = hopsworks.login(api_key_value=os.environ["API_KEY_HOPSWORKS"])
featurestore = project.get_feature_store()
modelregistry = project.get_model_registry()