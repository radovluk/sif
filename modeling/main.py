import logging
from logging.handlers import RotatingFileHandler

from fastapi import Request
from base import LocalGateway, base_logger
from base.influx_utils import fetch_all_sensor_data
from base.minio_utils import save_model_to_minio
from base.homecare_hub_utils import send_info, send_todo
from occupancy_model import prepare_data_for_occupancy_model, train_occupancy_model
from motion_analysis import train_motion_model, analyse_motion_patterns
from config import TRAINING_DATA_WINDOW_HOURS

# Configure logging
logging.basicConfig(
    handlers=[RotatingFileHandler("my_app.log", maxBytes=5_000_000, backupCount=5)],
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)

app = LocalGateway()
base_logger.info("Gateway initiated.")

async def create_occupancy_model_function(request: Request):
    base_logger.info("Function create_occupancy_model_function called.")
    data = await request.json()
    base_logger.info(f"Received data: {data}")

    # Fetch sensor data
    sensor_data = fetch_all_sensor_data(start_hours=TRAINING_DATA_WINDOW_HOURS, interval_hours=TRAINING_DATA_WINDOW_HOURS)
    sensor_data_df = prepare_data_for_occupancy_model(sensor_data)

    # Train the model
    room_stats = train_occupancy_model(sensor_data_df)

    # Save model to MinIO
    save_model_to_minio(room_stats)

    # Send info
    send_info("New occupancy model was successfully trained!", "New occupancy model was trained", 1)

    return {"status": "success"}

async def create_motion_model_function(request: Request):
    base_logger.info("Function create_motion_model_function called.")
    data = await request.json()
    base_logger.info(f"Received data: {data}")

    # TODO Complete this training function
    train_motion_model()
    send_info("New motion model was successfully trained!", "New motion model was deployed", 1)

    return {"status": "success"}

async def motion_analysis_function(request: Request):
    base_logger.info("Function motion_analysis_function called.")
    data = await request.json()
    base_logger.info(f"Received data: {data}")

    # TODO Complete this motion analysis function
    analyse_motion_patterns()
    send_info("New motion analysis was successfully deployed!", "New motion analysis was deployed", 1)

    return {"status": "success"}

# List of functions to deploy
functions_to_deploy = [
    {
        "func": create_occupancy_model_function,
        "name": "create_occupancy_model_function",
        "evts": "TrainOccupancyModelEvent",
        "method": "POST"
    },
    {
        "func": create_motion_model_function,
        "name": "create_motion_model_function",
        "evts": "TrainMotionModelEvent",
        "method": "POST"
    },
    {
        "func": motion_analysis_function,
        "name": "motion_analysis_function",
        "evts": "AnalyzeMotionEvent",
        "method": "POST"
    }
]

# Deploy all functions
for func_config in functions_to_deploy:
    app.deploy(
        func_config["func"],
        name=func_config["name"],
        evts=func_config["evts"],
        method=func_config["method"]
    )
    base_logger.info(f"{func_config['name']} deployed.")