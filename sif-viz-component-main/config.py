CURRENT_IP = "192.168.8.159" # Prague IP
# CURRENT_IP = "192.168.81.143" # Munich IP home

INFLUX_ORG = "wise2024"
INFLUX_TOKEN = os.environ.get("INFLUXDB_HOST", "192.168.81.143:8086")
INFLUX_USER = os.environ.get("INFLUXDB_USER", "admin")
INFLUX_PASS = os.environ.get("INFLUXDB_PASS", "secure_influx_iot_user")

SIF_SCHEDULER = os.environ.get("SCH_SERVICE_NAME", f"http://{CURRENT_IP}:30032")
# SIF_SCHEDULER = os.environ.get("SCH_SERVICE_NAME", "http://sif-edge.sif:9000/")

TODO_BUCKET = "todo_record"
INFO_BUCKET = "info_record"

BUCKETS = [TODO_BUCKET, INFO_BUCKET]