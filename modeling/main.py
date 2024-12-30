import logging
from logging.handlers import RotatingFileHandler

from fastapi import Request
from base import LocalGateway, base_logger
from base.influx_utils import fetch_all_sensor_data
from base.minio_utils import save_model_to_minio
from base.homecare_hub_utils import send_info, send_todo
from training import prepare_data_for_model, train_model
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
    sensor_data_df = prepare_data_for_model(sensor_data)

    # Train the model
    room_stats = train_model(sensor_data_df)

    # Save model to MinIO
    save_model_to_minio(room_stats)

    # Send info
    send_info("New model was successfully trained!", "New model was trained", 1)

    return {"status": "success"}

# Deploy the function
app.deploy(
    create_occupancy_model_function,
    name="create_occupancy_model_function",
    evts="TrainOccupancyModelEvent",
    method="POST"
)

base_logger.info("create_occupancy_model_function deployed.")