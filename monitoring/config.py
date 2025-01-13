import os

# CURRENT_IP = "192.168.8.159" # Prague IP
CURRENT_IP = "192.168.81.143" # Munich IP home

# Interval and wait time for retraining the occupancy model
TRAIN_OCCUPANCY_MODEL_INTERVAL = "12h"  # The model will be retrained every 12 hours
TRAIN_OCCUPANCY_MODEL_WAIT_TIME = "30s"  # Wait 30 seconds before starting the first retraining

# Interval and wait time for retraining the motion model
TRAIN_MOTION_MODEL_INTERVAL = "12h"  # The model will be retrained every 12 hours
TRAIN_MOTION_MODEL_WAIT_TIME = "15s"  # Wait 15 seconds before starting the first retraining

# Interval and wait time for analyzing motion data
ANALYSE_MOTION_INTERVAL = "24h"  # Motion data will be analyzed every 24 hours
ANALYSE_MOTION_WAIT_TIME = "20s"  # Wait 20 seconds before starting the first analysis

# Interval and wait time for retraining the burglary model
TRAIN_BURGLARY_MODEL_INTERVAL = "12h"  # The model will be retrained every 12 hours
TRAIN_BURGLARY_MODEL_WAIT_TIME = "30s"  # Wait 30 seconds before starting the first retraining

# Interval and wait time for checking burglary events
CHECK_BURGLARY_INTERVAL = "1h"  # Burglary events will be checked every 1 hour
CHECK_BURGLARY_WAIT_TIME = "40s"  # Wait 40 seconds before starting the first check

# Interval and wait time for checking emergency events
CHECK_EMERGENCY_INTERVAL = "30m"  # Emergency events will be checked every 30 minutes
CHECK_EMERGENCY_WAIT_TIME = "50s"  # Wait 50 seconds before starting the first check

# Threshold for emergency detection
TRESHOLD_FOR_EMERGENCY_DETECTION = 3  # Number of standard deviations from the mean to trigger an emergency

START_HOURS_FOR_EMERGENCY_DETECTION = 24 * 7 * 4 # Start of the interval for fetching data used for emergency detection
INTERVAL_HOURS_FOR_EMERGENCY_DETECTION = 24 * 7 * 4 # Duration of the interval for fetching data used for emergency detection

# How old data to use for retraining occupancy model
TRAINING_DATA_WINDOW_HOURS = 24 * 7 * 2

# Influx configuration
INFLUX_ORG = "wise2024"
INFLUX_TOKEN = os.environ.get("INFLUXDB_HOST", f"{CURRENT_IP}:8086")
INFLUX_USER = os.environ.get("INFLUXDB_USER", "admin")
INFLUX_PASS = os.environ.get("INFLUXDB_PASS", "secure_influx_iot_user")

# MinIO Configuration
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", f"{CURRENT_IP}:9090")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "9JyddmA0YyaIxd6Kl5pO")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "N8iyTd2nJGgBKUVvnrdDRlFvyZGOM5macCTAIADJ")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "models")
MINIO_OBJECT_NAME_PREFIX = os.environ.get("MINIO_OBJECT_NAME", "model")

# Visualization component URL
VIZ_COMPONENT_URL = f"http://{CURRENT_IP}:9000"

# Define sensors and buckets
SENSOR_DATA = {
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

BUCKET_DICT = {
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

# Validate that required variables are present
if not INFLUX_TOKEN or not INFLUX_USER or not INFLUX_PASS:
    raise ValueError("InfluxDB environment variables are not fully set.")
