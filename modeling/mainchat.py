import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import pandas as pd
from minio import Minio
from minio.error import S3Error
from influxdb_client import InfluxDBClient
from io import BytesIO, StringIO

# Influx configuration
INFLUX_ORG = "wise2024"
INFLUX_TOKEN = os.environ.get("INFLUXDB_HOST", "192.168.81.143:8086")  # Home IP
INFLUX_USER = os.environ.get("INFLUXDB_USER", "admin")
INFLUX_PASS = os.environ.get("INFLUXDB_PASS", "secure_influx_iot_user")

# MinIO Configuration
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "models")

sensor_data_mapping = {
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

# Setup Logging
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
    """
    Fetch data from InfluxDB for a specific bucket, measurement, and field.

    Parameters:
    - bucket (str): Name of the InfluxDB bucket.
    - measurement (str): Measurement name (e.g., "PIR", "battery").
    - field (str): Field name within the measurement.
    - hours (int): Number of hours to look back from the current time.

    Returns:
    - list of dicts: Fetched sensor data.
    """
    with InfluxDBClient(url=INFLUX_TOKEN, org=INFLUX_ORG, username=INFLUX_USER, password=INFLUX_PASS, verify_ssl=False) as client:
        p = {
            "_start": timedelta(hours=-hours),
        }

        query_api = client.query_api()
        query = f'''
            from(bucket: "{bucket}") |> range(start: _start)
            |> filter(fn: (r) => r["_measurement"] == "{measurement}")
            |> filter(fn: (r) => r["_type"] == "sensor-value")
            |> filter(fn: (r) => r["_field"] == "{field}")
        '''
        tables = query_api.query(query, params=p)
        obj = []
        logger.info(f"Fetched tables for bucket '{bucket}', measurement '{measurement}', field '{field}'.")

        for table in tables:
            for record in table.records:
                val = {}
                logger.debug(f"Processing record: {record}")
                # 'sensor' is a list based on bucket_dict mapping
                val["sensor"] = bucket_dict.get(bucket, ["unknown_sensor"])[0]
                val["bucket"] = bucket
                val["timestamp"] = record["_time"].timestamp() * 1000  # Convert to milliseconds
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

    Parameters:
    - buckets (list of str): List of bucket names.
    - measurement (str): Measurement name.
    - fields (list of str): List of field names.
    - hours (int): Number of hours to look back.

    Returns:
    - list of dicts: Aggregated sensor data from all specified buckets.
    """
    all_data = []
    for bucket in buckets:
        for field in fields:
            fetched_data = fetch_data(bucket=bucket, measurement=measurement, field=field, hours=hours)
            all_data.extend(fetched_data)
            logger.info(f"Fetched {len(fetched_data)} records from bucket '{bucket}', field '{field}'.")
    return all_data

def fetch_all_sensor_data(hours=168):
    """
    Fetch all sensor data (PIR and Magnetic Switch) within the specified time range.

    Parameters:
    - hours (int): Time range in hours to fetch data (default is 168 hours = 7 days).

    Returns:
    - list of dicts: Aggregated list of sensor data.
    """
    all_sensor_data = []
    # Fetch PIR sensor data
    pir_data = fetch_data_from_buckets(
        buckets=PIR_BUCKETS,
        measurement="PIR",
        fields=["roomID"],
        hours=hours
    )
    all_sensor_data.extend(pir_data)

    # Fetch Magnetic Switch data
    magnetic_switch_data = fetch_data_from_buckets(
        buckets=MAGNETIC_SWITCH_BUCKETS,
        measurement="MagneticSwitch",
        fields=["roomID"],
        hours=hours
    )
    all_sensor_data.extend(magnetic_switch_data)

    # Fetch Battery data
    battery_data = fetch_data_from_buckets(
        buckets=BATTERY_BUCKETS,
        measurement="battery",
        fields=["soc", "voltage"],
        hours=hours
    )
    all_sensor_data.extend(battery_data)

    logger.info(f"Total sensor data fetched: {len(all_sensor_data)} records.")
    return all_sensor_data

def prepare_data_for_model(sensor_data):
    """
    Prepare sensor data for model training.

    Parameters:
    - sensor_data (list of dicts): Raw sensor data.

    Returns:
    - pandas DataFrame: Preprocessed sensor data.
    """
    # Convert list of dictionaries to DataFrame
    df = pd.DataFrame(sensor_data)
    logger.info(f"Original data shape: {df.shape}")

    # Handle cases where 'sensor' is a list by extracting the first element
    if 'sensor' in df.columns:
        df['sensor'] = df['sensor'].apply(lambda x: x if isinstance(x, str) else 'unknown_sensor')
        logger.debug("Converted 'sensor' to string.")

    # Convert timestamp from milliseconds to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        logger.debug("Converted 'timestamp' to datetime.")

    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)
    logger.debug("Sorted DataFrame by 'timestamp'.")

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

def process_sensor_data(sensor_data_df):
    """
    Process sensor data to calculate duration spent in each room.

    Parameters:
    - sensor_data_df (pandas DataFrame): Preprocessed sensor data.

    Returns:
    - duration_df (pandas DataFrame): Duration information per group and room.
    """
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

    logger.info(f"Processed duration data shape: {duration_df.shape}")
    return duration_df

def compute_room_statistics(duration_df):
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

    logger.info(f"Computed room statistics:\n{room_stats}")
    return room_stats

def train_model(sensor_data_df):
    """
    Train an anomaly detection model based on sensor data.

    Parameters:
    - sensor_data_df (pandas DataFrame): Preprocessed sensor data.

    Returns:
    - room_stats (pandas DataFrame): Statistics per room.
    """
    # Process sensor data to get duration per room
    duration_df = process_sensor_data(sensor_data_df)

    # Compute statistics for each room
    room_stats = compute_room_statistics(duration_df)

    return room_stats

def initialize_minio_client(minio_config):
    """
    Initialize and return a MinIO client.

    Parameters:
    - minio_config (dict): Dictionary containing MinIO configuration:
        {
            'endpoint': 'play.min.io:9000',
            'access_key': 'YOURACCESSKEY',
            'secret_key': 'YOURSECRETKEY',
            'secure': True  # False if using HTTP
        }

    Returns:
    - client (Minio): Initialized MinIO client.
    """
    try:
        client = Minio(
            endpoint=minio_config['endpoint'],
            access_key=minio_config['access_key'],
            secret_key=minio_config['secret_key'],
            secure=minio_config.get('secure', True)
        )
        logger.info("Initialized MinIO client successfully.")
        return client
    except Exception as e:
        logger.error(f"Error initializing MinIO client: {e}")
        return None

def ensure_bucket_exists(client, bucket_name):
    """
    Ensure that the specified bucket exists in MinIO. Create it if it doesn't.

    Parameters:
    - client (Minio): Initialized MinIO client.
    - bucket_name (str): Name of the bucket to check/create.

    Returns:
    - None
    """
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            logger.info(f"Bucket '{bucket_name}' created.")
        else:
            logger.info(f"Bucket '{bucket_name}' already exists.")
    except S3Error as e:
        logger.error(f"Error checking/creating bucket '{bucket_name}': {e}")

def save_model_to_minio(room_stats, minio_config):
    """
    Save the room statistics model to MinIO.

    Parameters:
    - room_stats (pandas DataFrame): Statistics per room.
    - minio_config (dict): Dictionary containing MinIO configuration:
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
        logger.error("Failed to initialize MinIO client. Model not saved.")
        return

    # Ensure the bucket exists
    ensure_bucket_exists(client, minio_config['bucket_name'])

    # Upload the model to MinIO
    object_name = minio_config['object_name']
    try:
        # Convert JSON string to bytes
        data = model_json.encode('utf-8')
        data_stream = BytesIO(data)
        data_length = len(data)

        # Upload the object
        client.put_object(
            bucket_name=minio_config['bucket_name'],
            object_name=object_name,
            data=data_stream,
            length=data_length,
            content_type='application/json'
        )
        logger.info(f"Model saved to MinIO as '{object_name}' in bucket '{minio_config['bucket_name']}'.")
    except S3Error as e:
        logger.error(f"Error uploading model to MinIO: {e}")

def load_model_from_minio(minio_config):
    """
    Load the room statistics model from MinIO.

    Parameters:
    - minio_config (dict): Dictionary containing MinIO configuration:
        {
            'endpoint': 'play.min.io:9000',
            'access_key': 'YOURACCESSKEY',
            'secret_key': 'YOURSECRETKEY',
            'secure': True,  # False if using HTTP
            'bucket_name': 'models',
            'object_name': 'room_stats.json'  # or .csv, etc.
        }

    Returns:
    - room_stats (pandas DataFrame): Loaded room statistics.
    """
    # Initialize MinIO client
    client = initialize_minio_client(minio_config)
    if client is None:
        logger.error("Failed to initialize MinIO client. Model not loaded.")
        return None

    # Download the object
    object_name = minio_config['object_name']
    try:
        response = client.get_object(
            bucket_name=minio_config['bucket_name'],
            object_name=object_name
        )
        data = response.read()
        response.close()
        response.release_conn()
        logger.info(f"Model '{object_name}' downloaded from MinIO bucket '{minio_config['bucket_name']}'.")
    except S3Error as e:
        logger.error(f"Error downloading model from MinIO: {e}")
        return None

    # Deserialize JSON to DataFrame
    try:
        model_json = data.decode('utf-8')
        room_stats = pd.read_json(StringIO(model_json), orient='records')
        logger.info("Model deserialized successfully.")
        return room_stats
    except Exception as e:
        logger.error(f"Error deserializing model JSON: {e}")
        return None

def main():
    """
    Main function to execute the training and saving of the model.
    """
    # Fetch all sensor data for the past 14 days (24*7*2 hours)
    sensor_data = fetch_all_sensor_data(hours=24*7*2)
    logger.info(f"Fetched a total of {len(sensor_data)} sensor records.")

    # Prepare the data for the model
    sensor_data_df = prepare_data_for_model(sensor_data)
    logger.info(f"Prepared data for model training. DataFrame shape: {sensor_data_df.shape}")

    # Train the model to compute room statistics
    room_stats = train_model(sensor_data_df)
    logger.info(f"Trained model. Room statistics:\n{room_stats}")

    # Define MinIO configuration
    minio_config = {
        'endpoint': MINIO_ENDPOINT,
        'access_key': MINIO_ACCESS_KEY,
        'secret_key': MINIO_SECRET_KEY,
        'secure': False if MINIO_ENDPOINT.startswith("localhost") else True,  # Assuming non-secure for localhost
        'bucket_name': MINIO_BUCKET,
        'object_name': 'room_stats.json'
    }

    # Save the trained model to MinIO
    save_model_to_minio(room_stats, minio_config)

if __name__ == "__main__":
    main()
