import logging
from logging.handlers import RotatingFileHandler

from fastapi import Request
from base import LocalGateway, base_logger
from base.influx_utils import fetch_all_sensor_data
from base.minio_utils import save_model_to_minio
from base.homecare_hub_utils import send_info, send_todo
from occupancy_model import prepare_data_for_occupancy_model, train_occupancy_model
from burglary_model import train_burglary_model
from motion_model import train_motion_model
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
    save_model_to_minio(room_stats, "occupancy")

    # Send info
    send_info("🏥 New Occupancy Model Trained Successfully! 🤖", "👩‍⚕️ A new occupancy model has been trained to assist with patient monitoring. 🛏️📈",1)

    return {"status": "success"}

async def create_motion_model_function(request: Request):
    base_logger.info("Function create_motion_model_function called.")
    data = await request.json()
    base_logger.info(f"Received data: {data}")

    # Train the model
    motion_model = train_motion_model(start_hours=24*7, interval_hours=24*7, time_threshold_seconds=1800)
    
    # Save model to MinIO
    save_model_to_minio(motion_model, "motion")

    # Send info
    send_info("🚶‍♂️ New Motion Model Created Successfully! 🏃‍♀️","🚀 A new motion model has been deployed. 🏠📊",1)

    return {"status": "success"}

async def create_burglary_model_function(request: Request):
    base_logger.info("Function create_burglary_model_function called.")
    data = await request.json()
    base_logger.info(f"Received data: {data}")

    train_burglary_model(start_hours=24*7*6, interval_hours=24*7*6, time_threshold_seconds=1800)

    # Send info
    send_info("🏠🔍 New Burglary Model Trained Successfully! 🚔","📊 A new burglary model has been trained and is ready to enhance home security. 🔒🏡",1)

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
        "func": create_burglary_model_function,
        "name": "create_burglary_model_function",
        "evts": "TrainBurglaryModelEvent",
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