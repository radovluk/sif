import os
import sys
import json
import urllib3
import logging
import pickle
import time

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from minio import Minio
from minio.error import S3Error
from io import BytesIO

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point, WritePrecision
from logging.handlers import RotatingFileHandler
from influxdb_client.client.write_api import SYNCHRONOUS
from base import LocalGateway, base_logger
from fastapi import Request

# how old data to use for retraiing
FETCHED_DATA_FOR_RETRAINING_HOURS = 24*7*2

# Influx configuration
INFLUX_ORG = "wise2024"
# INFLUX_TOKEN = os.environ.get("INFLUXDB_HOST", "131.159.85.125:8086")
INFLUX_TOKEN = os.environ.get("INFLUXDB_HOST", "192.168.81.143:8086") ### home IP
INFLUX_USER = os.environ.get("INFLUXDB_USER", "admin")
INFLUX_PASS = os.environ.get("INFLUXDB_PASS", "secure_influx_iot_user")

# MinIO Configuration
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "192.168.81.143:9090")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "9JyddmA0YyaIxd6Kl5pO")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "N8iyTd2nJGgBKUVvnrdDRlFvyZGOM5macCTAIADJ")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "models")
MINIO_OBJECT_NAME_PREFIX = os.environ.get("MINIO_OBJECT_NAME", "model")
LATEST_POINTER_FILE = "latest.txt"  # This file will store the name of the latest model object

VIZ_COMPONENT_URL = "http://192.168.81.143:9000"

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
        base_logger.info(tables)
        for table in tables:
            for record in table.records:
                val = {}
                base_logger.info(record)
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

def initialize_minio_client():
    """
    Initialize and return a MinIO client.
    Returns:
    - client (Minio): Initialized MinIO client.
    """
    try:
        client = Minio(
            endpoint=MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )
        base_logger.info("Initialized MinIO client successfully.")
        return client
    except Exception as e:
        base_logger.error(f"Error initializing MinIO client: {e}")
        return None

def save_model_to_minio(room_stats):
    """
    Save the room statistics model to MinIO, keeping previous versions.
    It also updates a 'latest.txt' file with the name of the newly saved model.
    """

    # Serialize the model (room_stats) to JSON
    model_json = room_stats.to_json(orient='records', date_format='iso')

    # Initialize MinIO client
    client = initialize_minio_client()
    if client is None:
        base_logger.error("Failed to initialize MinIO client. Model not saved.")
        return

    # Ensure the bucket exists
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)
        base_logger.info(f"Bucket '{MINIO_BUCKET}' created.")
    else:
        base_logger.info(f"Bucket '{MINIO_BUCKET}' already exists.")

    # Create a timestamped object name to keep old versions
    timestamp_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    object_name = f"{MINIO_OBJECT_NAME_PREFIX}_{timestamp_str}.json"

    try:
        # Convert JSON string to bytes
        data = model_json.encode('utf-8')
        data_stream = BytesIO(data)
        data_length = len(data)

        # Upload the versioned model
        client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            data=data_stream,
            length=data_length,
            content_type='application/json'
        )
        base_logger.info(f"Model saved to MinIO as '{object_name}' in bucket '{MINIO_BUCKET}'.")

        # Update the "latest" pointer
        latest_data = object_name.encode('utf-8')
        latest_stream = BytesIO(latest_data)
        client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=LATEST_POINTER_FILE,
            data=latest_stream,
            length=len(latest_data),
            content_type='text/plain'
        )
        base_logger.info(f"'{LATEST_POINTER_FILE}' updated to point to '{object_name}'.")

    except S3Error as e:
        base_logger.error(f"Error uploading model to MinIO: {e}")

def load_model_from_minio():
    """
    Load the latest room statistics model from MinIO by first reading the 'latest.txt'
    file to determine the newest model file.
    Returns:
    - room_stats (pandas DataFrame): Loaded room statistics.
    """
    # Initialize MinIO client
    client = initialize_minio_client()
    if client is None:
        base_logger.error("Failed to initialize MinIO client. Model not loaded.")
        return None

    # First, get the name of the latest model from 'latest.txt'
    try:
        response = client.get_object(
            bucket_name=MINIO_BUCKET,
            object_name=LATEST_POINTER_FILE
        )
        latest_object_name = response.read().decode('utf-8').strip()
        response.close()
        response.release_conn()
        base_logger.info(f"Latest model object determined from '{LATEST_POINTER_FILE}': '{latest_object_name}'")
    except S3Error as e:
        base_logger.error(f"Error reading latest model pointer file '{LATEST_POINTER_FILE}': {e}")
        return None

    # Now download the latest model object
    try:
        response = client.get_object(
            bucket_name=MINIO_BUCKET,
            object_name=latest_object_name
        )
        data = response.read()
        response.close()
        response.release_conn()
        base_logger.info(f"Model '{latest_object_name}' downloaded from MinIO bucket '{MINIO_BUCKET}'.")
    except S3Error as e:
        base_logger.error(f"Error downloading model '{latest_object_name}' from MinIO: {e}")
        return None

    # Deserialize JSON to DataFrame
    try:
        model_json = data.decode('utf-8')
        room_stats = pd.read_json(StringIO(model_json), orient='records')
        base_logger.info("Model deserialized successfully.")
        return room_stats
    except Exception as e:
        base_logger.error(f"Error deserializing model JSON: {e}")
        return None

def prepare_data_for_model(sensor_data):
    """
    Prepare sensor data for model training.

    :param sensor_data: List of sensor data dictionaries.
    :return: Preprocessed pandas DataFrame.
    """
    # Convert list of dictionaries to DataFrame
    df = pd.DataFrame(sensor_data)
    base_logger.info(f"Original data shape: {df.shape}")

    # Handle cases where 'sensor' is a list by extracting the first element
    if 'sensor' in df.columns:
        df['sensor'] = df['sensor'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 'unknown_sensor')
        base_logger.debug("Converted 'sensor' from list to string.")

    # Convert timestamp from milliseconds to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        base_logger.debug("Converted 'timestamp' to datetime.")

    # Sort by timestamp
    df = df.sort_values('timestamp')

    # Encode categorical variables
    if 'sensor' in df.columns:
        le = LabelEncoder()
        try:
            df['sensor_encoded'] = le.fit_transform(df['sensor'])
            base_logger.debug("Encoded 'sensor' successfully.")
        except Exception as e:
            base_logger.error(f"Error encoding 'sensor' column: {e}")
            df['sensor_encoded'] = 0  # Assign a default value or handle as needed

    return df


    """
    Compute mean and standard deviation of duration_seconds per room.

    Parameters:
    - duration_df (pandas DataFrame): Duration information.

    Returns:
    - room_stats (pandas DataFrame): Statistics per room.
    """
    # Group by 'value' (room) and calculate statistics
    room_stats = duration_df.groupby('value')['duration_seconds'].agg(['mean', 'std']).reset_index()

    # Handle cases where std might be NaN (e.g., only one entry for a room)
    room_stats['std'] = room_stats['std'].fillna(0)

    base_logger.info(f"Computed room statistics:\n{room_stats}")
    return room_stats

def train_model(sensor_data_df):
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

    return room_stats

def send_info(summary, detail, level):
    """
    Sends an Information item to the FastAPI /api/info endpoint.

    Args:
        summary (str): A brief summary of the information.
        detail (dict or object): Detailed information or description.
        level (int): The priority or level of the information.
    """
    # Generate the current Unix timestamp in milliseconds
    current_timestamp = int(time.time() * 1000)

    # Serialize the detail object to a JSON-formatted string
    try:
        # If 'detail' is a dictionary or a serializable object
        serialized_detail = json.dumps(detail)
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to serialize 'detail': {e}")
        # Fallback to string conversion if serialization fails
        serialized_detail = str(detail)

    # Create the Information item with 'detail' as a string
    info_item = {
        "timestamp": current_timestamp,
        "summary": summary,
        "detail": serialized_detail,
        "level": level
    }

    # Convert the Python dictionary to a JSON string
    try:
        encoded_data = json.dumps(info_item).encode('utf-8')
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to encode Information item to JSON: {e}")
        return

    # Initialize the PoolManager
    http = urllib3.PoolManager()

    # Define the URL
    url = f"{VIZ_COMPONENT_URL}/api/info"

    # Set the headers
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        # Send the POST request
        response = http.request(
            'POST',
            url,
            body=encoded_data,
            headers=headers
        )
        
        # Check the response status
        if response.status in [200, 201]:
            logger.info("Information item saved successfully.")
            # Optionally, parse the response data
            if response.data:
                try:
                    response_data = json.loads(response.data.decode('utf-8'))
                    logger.info(f"Response: {response_data}")
                except json.JSONDecodeError:
                    logger.warning("Response data is not valid JSON.")
        else:
            logger.error(f"Failed to save Information item. Status Code: {response.status}")
            logger.error(f"Response: {response.data.decode('utf-8')}")
    except urllib3.exceptions.HTTPError as e:
        logger.error(f"HTTP error occurred: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


################ start of the main app ################
#######################################################
if INFLUX_TOKEN is None or INFLUX_USER is None or INFLUX_PASS is None:
    raise ValueError("Missing env variables")

app = LocalGateway()
base_logger.info("Gateway initiated.")

async def create_occupancy_model_function(request: Request):
    base_logger.info("Function create occupancy model called.")
    data = await request.json()
    base_logger.info(f"Function create_occupancy_model_function received data: {data}")
    base_logger.info("Now I will retrain and store the new model to Minio.")
    sensor_data = fetch_all_sensor_data(hours=FETCHED_DATA_FOR_RETRAINING_HOURS)
    sensor_data_df = prepare_data_for_model(sensor_data)
    room_stats = train_model(sensor_data_df)
    save_model_to_minio(room_stats)
    send_info("New model was successfully trained!", "New model was trained", 1)
    return {"status": "success"}

app.deploy(
    create_occupancy_model_function,
    name="create_occupancy_model_function",
    evts="TrainOccupancyModelEvent",
    method="POST"
)
base_logger.info("create_occupancy_model_function deployed.")