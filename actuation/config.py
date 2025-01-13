import os

# CURRENT_IP = "192.168.8.159" # Prague IP
CURRENT_IP = "192.168.81.143" # Munich IP home

# How old data to use for retraining
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
