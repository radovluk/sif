from base import LocalGateway, base_logger, PeriodicTrigger, BaseEventFabric, OneShotTrigger
from fastapi import Request
import pandas as pd
from io import StringIO
import os
from minio import Minio
from minio.error import S3Error
import json
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timedelta
from sklearn.preprocessing import LabelEncoder

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

TRAIN_MODEL_INTERVAL = "4m"
CHECK_EMERGENCY_INTERVAL = "2m"

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

     # Create a flag that indicates when the 'value' changes compared to the previous row
    df['room_change'] = (df['value'] != df['value'].shift(1)).astype(int)

    # Create a cumulative sum of the 'room_change' flag to assign a unique group ID to each consecutive block
    df['group_id'] = df['room_change'].cumsum()

    # Group by 'group_id' and 'value' to handle each room separately
    duration_df = df.groupby(['group_id', 'value']).agg(
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max')
    ).reset_index()

    # Calculate duration as the difference between end_time and start_time
    duration_df['duration'] = duration_df['end_time'] - duration_df['start_time']

    # Convert 'duration' to total seconds for easier numerical processing
    duration_df['duration_seconds'] = duration_df['duration'].apply(lambda x: pd.to_timedelta(x).total_seconds())

    return duration_df

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

def detect_emergency(fetched_data, room_stats, threshold=3):
    # Check if fetched_data is empty
    if fetched_data.empty:
        # If there's no data, we cannot determine an emergency
        return False, "No data fetched. Cannot detect emergency."

    # Get the last row of the fetched_data DataFrame
    last_row = fetched_data.iloc[-1]
    room = last_row['value']
    current_duration = last_row['duration_seconds']

    # Find the corresponding room stats
    stats = room_stats[room_stats['value'] == room]
    if stats.empty:
        # If we have no stats for this room, we cannot determine an emergency
        return False, f"No stats found for room '{room}'. Cannot detect emergency."

    mean = stats['mean'].values[0]
    std = stats['std'].values[0]

    # If std == 0, handle that scenario
    if std == 0:
        if current_duration != mean:
            return True, f"Emergency detected in {room}: duration={current_duration}, mean={mean}, std={std}"
        else:
            return False, f"No emergency in {room}: duration={current_duration} equals mean={mean} (std=0)"
    else:
        # Compute acceptable range
        lower_bound = mean - threshold * std
        upper_bound = mean + threshold * std

        if current_duration < lower_bound or current_duration > upper_bound:
            return True, (f"Emergency detected in {room}: duration={current_duration}, "
                          f"mean={mean}, std={std}, threshold={threshold}, "
                          f"range=({lower_bound}, {upper_bound})")
        else:
            return False, (f"No emergency in {room}: duration={current_duration} is within "
                           f"mean ± {threshold} * std = ({lower_bound}, {upper_bound})")


################ start of the main app ################
#######################################################

class TrainOccupancyModelEvent(BaseEventFabric):
    def __init__(self):
        super(TrainOccupancyModelEvent, self).__init__()
    
    def call(self, *args, **kwargs):
        evt_name = "TrainOccupancyModelEvent"
        data = {"message": "Now I need to retrain my model"}
        base_logger.info(f"Event generated: {evt_name} with data {data}")
        return evt_name, data

class CheckEmergencyEvent(BaseEventFabric):
    def __init__(self):
        super(CheckEmergencyEvent, self).__init__()
    
    def call(self, *args, **kwargs):
        evt_name = "CheckEmergencyEvent"
        data = {"message": "Now I will check the emergency"}
        base_logger.info(f"Event generated: {evt_name} with data {data}")
        return evt_name, data

class EmergencyEvent(BaseEventFabric):
    def __init__(self, message):
        super(EmergencyEvent, self).__init__()
        self.message = message
    
    def call(self, *args, **kwargs):
        evt_name = "EmergencyEvent"
        data = {"message": "Now I will trigger emergency"}
        base_logger.info(f"Event generated: {evt_name} with message {self.message}")
        return evt_name, self.message

async def check_emergency_detection_function(request: Request):
    base_logger.info("Function check emergency called.")
    data = await request.json()
    base_logger.info(f"Function check_emergency_detection_function received data: {data}")
    room_stats = load_model_from_minio()
    sensor_data = fetch_all_sensor_data(hours=3) #fetch the data of last three hours
    fetched_data_df = prepare_data_for_model(sensor_data)
    emergency_detected, message = detect_emergency(fetched_data_df, room_stats)
    if True: # TODO change this emergency_detected:
        base_logger.info(f"Emergency detected: {message}")
        emergency_event = EmergencyEvent(message)
        base_logger.info("emergency_event instatiated. Calling emergency notification function")
        trigger = OneShotTrigger(emergency_event)
    else:
        base_logger.info(f"No emergency detected: {message}")
    return {"status": "success"}

# Instantiate the custom event fabrics
train_occupancy_model_event = TrainOccupancyModelEvent()
base_logger.info("train_occupancy_model_event instatiated.")
check_emergency_event = CheckEmergencyEvent()
base_logger.info("check_emergency_event instatiated.")

# Create a periodic trigger for the train_occupancy_model_event event
periodicTriggerTrainModel = PeriodicTrigger(
    train_occupancy_model_event,
    duration=TRAIN_MODEL_INTERVAL,
    wait_time="1m"  # Starts after 30s, then triggers every 30 seconds
)
base_logger.info("PeriodicTrigger for train_occupancy_model_event set: Starts after 30s, then triggers every 2 minutes")

# Create a periodic trigger for the check_emergency_event event
periodicTriggerCheckEmergency = PeriodicTrigger(
    check_emergency_event,
    duration=CHECK_EMERGENCY_INTERVAL,
    wait_time="30s"  # Starts after 1 minute, then triggers every 30 seconds
)
base_logger.info("PeriodicTrigger for check_emergency_event set: Starts after 1 minute, then triggers every 30 seconds")

# Instantiate the LocalGateway
app = LocalGateway()
base_logger.info("Gateway initiated.")

# Deploy the function
app.deploy(check_emergency_detection_function, name="check_emergency_detection_function", evts="CheckEmergencyEvent", method="POST")
base_logger.info("check_emergency_detection_function deployed.")