import os
import sys
import json
import urllib3
import logging
import pickle

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from minio import Minio
from minio.error import S3Error

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point, WritePrecision
from logging.handlers import RotatingFileHandler
from influxdb_client.client.write_api import SYNCHRONOUS
from base import LocalGateway
from fastapi import Request

# Influx configuration
INFLUX_ORG = "wise2024"
# INFLUX_TOKEN = os.environ.get("INFLUXDB_HOST", "131.159.85.125:8086")
INFLUX_TOKEN = os.environ.get("INFLUXDB_HOST", "192.168.81.143:8086") ### home IP
INFLUX_USER = os.environ.get("INFLUXDB_USER", "admin")
INFLUX_PASS = os.environ.get("INFLUXDB_PASS", "secure_influx_iot_user")

# MinIO Configuration
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "models")

sensor_data = {
    "kitchen": {
        "battery": "1_5_10", 
        "PIR": "1_5_9"
    },
    "livingroom": {
        "PIR": "1_4_7",
        "battery": "1_4_8",
        "magnetic_switch": "1_4_11"
    },
    "bathroom": {
        "PIR": "1_3_6",
        "battery": "1_3_5"
    }
}

bucket_dict = {
    "1_5_10": ["kitchen_battery"],
    "1_5_9": ["kitchen_PIR"],
    "1_4_7": ["livingroom_PIR"],
    "1_4_8": ["livingroom_battery"],
    "1_4_11": ["livingroom_magnetic_switch"],
    "1_3_6": ["bathroom_PIR"],
    "1_3_5": ["bathroom_battery"]
}

BUCKETS = ["1_5_10", "1_5_9", "1_4_7", "1_4_8", "1_4_11", "1_3_6", "1_3_5"]
PIR_BUCKETS = ["1_5_9", "1_4_7", "1_3_6"]
MAGNETIC_SWITCH_BUCKETS = ["1_4_11"]
BATTERY_BUCKETS = ["1_5_10", "1_4_8"]

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler("log.log", maxBytes=1e9, backupCount=2),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("viz_component")

def fetch_data(bucket, measurement, field, hours=24):
    with InfluxDBClient(url=INFLUX_TOKEN, org=INFLUX_ORG, username=INFLUX_USER, password=INFLUX_PASS, verify_ssl=False) as client:
        p = {
            "_start": timedelta(hours=-hours),
        }

        query_api = client.query_api()
        tables = query_api.query(f'''
                                 from(bucket: "{bucket}") |> range(start: _start)
                                 |> filter(fn: (r) => r["_measurement"] == "{measurement}")
                                 |> filter(fn: (r) => r["_type"] == "{"sensor-value"}")
                                 |> filter(fn: (r) => r["_field"] == "{field}")
                                 ''', params=p)
        obj = []
        logger.info(tables)
        for table in tables:
            for record in table.records:
                val = {}
                logger.info(record)
                val["sensor"] = bucket_dict[bucket]
                val["bucket"] = bucket
                val["timestamp"] = record["_time"].timestamp() * 1000
                val["value"] = record["_value"]
                if bucket in BATTERY_BUCKETS:
                    val["field"] = record["_field"]
                    val["type"] = "battery"
                else:
                    val["type"] = "sensor"
                if len(val.keys()) != 0:
                    obj.append(val)

        return obj

def fetch_data_from_buckets(buckets, measurement, fields, hours=1):
    """
    Fetch data from multiple buckets, measurements, and fields.

    :param buckets: List of bucket names
    :param measurement: Measurement name (e.g., "PIR", "battery")
    :param fields: List of field names (e.g., "roomID", "soc", "voltage")
    :param days: Number of days for the data range (default is 7)
    :return: List of fetched data
    """
    all_data = []
    for bucket in buckets:
        for field in fields:
            all_data.extend(fetch_data(bucket=bucket, measurement=measurement, field=field, hours=hours))
    return all_data

def fetch_all_data(hours=1):
    all_data = []
    # Fetch sensor data
    all_data.extend(fetch_data_from_buckets(PIR_BUCKETS, "PIR", ["roomID"], hours))
    all_data.extend(fetch_data_from_buckets(MAGNETIC_SWITCH_BUCKETS, "MagneticSwitch", ["roomID"], hours))
    # Fetch battery data
    all_data.extend(fetch_data_from_buckets(BATTERY_BUCKETS, "battery", ["soc", "voltage"], hours))
    return all_data

def fetch_battery_info(hours=1):
    return fetch_data_from_buckets(BATTERY_BUCKETS, "battery", ["soc", "voltage"], hours)

def fetch_all_sensor_data(hours=1):
    """
    Fetch all sensor data (PIR and Magnetic Switch) within the specified time range.

    :param hours: Time range in hours to fetch data.
    :return: Aggregated list of sensor data.
    """
    all_sensor_data = []
    # Fetch PIR sensor data
    pir_data = fetch_data_from_buckets(
        buckets=PIR_BUCKETS,
        measurement="PIR",
        fields=["roomID"],  # Adjust fields as necessary
        hours=hours
    )
    all_sensor_data.extend(pir_data)

    # Fetch Magnetic Switch data
    magnetic_switch_data = fetch_data_from_buckets(
        buckets=MAGNETIC_SWITCH_BUCKETS,
        measurement="MagneticSwitch",
        fields=["roomID"],  # Adjust fields as necessary
        hours=hours
    )
    all_sensor_data.extend(magnetic_switch_data)

    return all_sensor_data

def initialize_minio_client(minio_config):
    """
    Initialize and return a MinIO client.
    
    Parameters:
    - minio_config: Dictionary containing MinIO configuration:
        {
            'endpoint': 'play.min.io:9000',
            'access_key': 'YOURACCESSKEY',
            'secret_key': 'YOURSECRETKEY',
            'secure': True  # False if using HTTP
        }
    
    Returns:
    - client: Minio client object
    """
    try:
        client = Minio(
            endpoint=minio_config['endpoint'],
            access_key=minio_config['access_key'],
            secret_key=minio_config['secret_key'],
            secure=minio_config.get('secure', True)
        )
        return client
    except Exception as e:
        print(f"Error initializing MinIO client: {e}")
        return None

def ensure_bucket_exists(client, bucket_name):
    """
    Ensure that the specified bucket exists in MinIO. Create it if it doesn't.
    
    Parameters:
    - client: Minio client object
    - bucket_name: Name of the bucket to check/create
    
    Returns:
    - None
    """
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"Bucket '{bucket_name}' created.")
        else:
            print(f"Bucket '{bucket_name}' already exists.")
    except S3Error as e:
        print(f"Error checking/creating bucket: {e}")

def save_model_to_minio(room_stats):
    """
    Save the room statistics model to MinIO.
    
    Parameters:
    - room_stats: pandas DataFrame containing mean and std of duration_seconds per room
    - minio_config: Dictionary containing MinIO configuration:
        {
            'endpoint': 'play.min.io:9000',
            'access_key': 'YOURACCESSKEY',
            'secret_key': 'YOURSECRETKEY',
            'secure': True,  # False if using HTTP
            'bucket_name': 'models',
            'object_name': 'room_stats.json'  # or .csv, etc.
        }
    
    Returns:
    - None
    """
    # Serialize the model (room_stats) to JSON
    model_json = room_stats.to_json(orient='records', date_format='iso')
    
    # Initialize MinIO client
    client = initialize_minio_client(minio_config)
    if client is None:
        print("Failed to initialize MinIO client.")
        return
    
    # Ensure the bucket exists
    ensure_bucket_exists(client, minio_config['bucket_name'])
    
    # Upload the model to MinIO
    object_name = minio_config['object_name']
    try:
        # Convert JSON string to bytes
        data = model_json.encode('utf-8')
        data_stream = io.BytesIO(data)
        data_length = len(data)
        
        # Upload the object
        client.put_object(
            bucket_name=minio_config['bucket_name'],
            object_name=object_name,
            data=data_stream,
            length=data_length,
            content_type='application/json'
        )
        print(f"Model saved to MinIO as '{object_name}' in bucket '{minio_config['bucket_name']}'.")
    except S3Error as e:
        print(f"Error uploading model to MinIO: {e}")

def prepare_data_for_model(sensor_data):
    """
    Prepare sensor data for model training.

    :param sensor_data: List of sensor data dictionaries.
    :return: Preprocessed pandas DataFrame.
    """
    # Convert list of dictionaries to DataFrame
    df = pd.DataFrame(sensor_data)
    logger.info(f"Original data shape: {df.shape}")

    # Handle cases where 'sensor' is a list by extracting the first element
    if 'sensor' in df.columns:
        df['sensor'] = df['sensor'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 'unknown_sensor')
        logger.debug("Converted 'sensor' from list to string.")

    # Convert timestamp from milliseconds to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        logger.debug("Converted 'timestamp' to datetime.")

    # Sort by timestamp
    df = df.sort_values('timestamp')

    # Encode categorical variables
    if 'sensor' in df.columns:
        le = LabelEncoder()
        try:
            df['sensor_encoded'] = le.fit_transform(df['sensor'])
            logger.debug("Encoded 'sensor' successfully.")
        except Exception as e:
            logger.error(f"Error encoding 'sensor' column: {e}")
            df['sensor_encoded'] = 0  # Assign a default value or handle as needed

    return df

def train_model(sensor_data_df):
    # parse time stamps
    sensor_data_df['timestamp'] = sensor_data_df.to_datetime(df['timestamp'])

    # Create a flag that indicates when the 'value' changes compared to the previous row
    sensor_data_df['room_change'] = (sensor_data_df['value'] != sensor_data_df['value'].shift(1)).astype(int)

    # Create a cumulative sum of the 'room_change' flag to assign a unique group ID to each consecutive block
    sensor_data_df['group_id'] = sensor_data_df['room_change'].cumsum()

    # Group by 'group_id' and 'value' to handle each room separately
    duration_df = sensor_data_df.groupby(['group_id', 'value']).agg(
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max')
    ).reset_index()

    # Calculate duration as the difference between end_time and start_time
    duration_df['duration'] = duration_df['end_time'] - duration_df['start_time']

    # Convert 'duration' to total seconds for easier numerical processing
    duration_df['duration_seconds'] = duration_df['duration'].apply(lambda x: pd.to_timedelta(x).total_seconds())

    # Group by 'value' (room) and calculate statistics
    room_stats = duration_df.groupby('value')['duration_seconds'].agg(['mean', 'std']).reset_index()

    # Handle cases where std might be NaN (e.g., only one entry for a room)
    room_stats['std'] = room_stats['std'].fillna(0)

################ start of the main app ################
#######################################################

sensor_data = fetch_all_sensor_data(hours=24*7*2)
sensor_data_df = prepare_data_for_model(sensor_data)
room_stats = train_model(sensor_data_df)
save_model_to_minio = (room_stats)

# if INFLUX_TOKEN is None or INFLUX_USER is None or INFLUX_PASS is None:
#     raise ValueError("Missing env variables")

# app = LocalGateway()
# base_logger.info("Gateway initiated.")

# async def create_occupancy_model_function(request: Request):
#     base_logger.info("Function create occupancy model called.")
#     data = await request.json()
#     base_logger.info(f"Function create_occupancy_model_function received data: {data}")
#     base_logger.info("Now I will retrain and store the new model to Minio.")
#     # TODO Retrain and store the model to Minio
#     return {"status": "success"}

# app.deploy(
#     create_occupancy_model_function,
#     name="create_occupancy_model_function",
#     evts="TrainOccupancyModelEvent",
#     method="POST"
# )

# base_logger.info("create_occupancy_model_function app deployed.")