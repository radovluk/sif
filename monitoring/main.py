import logging
import os

from fastapi import Request

from base import BaseEventFabric, PeriodicTrigger, OneShotTrigger
from base.gateway import LocalGateway
from base.homecare_hub_utils import send_info
from base.influx_utils import fetch_all_sensor_data
from base.minio_utils import load_model_from_minio
from config import (
    TRAIN_MODEL_INTERVAL,
    CHECK_EMERGENCY_INTERVAL,
    TRAIN_MODEL_WAIT_TIME,
    CHECK_EMERGENCY_WAIT_TIME,
    FETCH_START_HOURS,
    FETCH_INTERVAL_HOURS
)
from detection import detect_emergency, prepare_data_for_detection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TrainOccupancyModelEvent(BaseEventFabric):
    """
    Event class responsible for triggering an occupancy model retraining.
    """
    def call(self, *args, **kwargs):
        """
        Execute when the event is triggered.

        :return: Tuple of (event_name, data_dict)
        """
        event_name = "TrainOccupancyModelEvent"
        data = {"message": "Retraining the occupancy model"}
        logger.info(f"Event generated: {event_name} with data {data}")
        return event_name, data


class CheckEmergencyEvent(BaseEventFabric):
    """
    Event class responsible for checking emergency conditions.
    """
    def call(self, *args, **kwargs):
        """
        Execute when the event is triggered.

        :return: Tuple of (event_name, data_dict)
        """
        event_name = "CheckEmergencyEvent"
        data = {"message": "Checking for emergencies"}
        logger.info(f"Event generated: {event_name} with data {data}")
        return event_name, data


class EmergencyEvent(BaseEventFabric):
    """
    Event class triggered when an emergency condition is detected.
    """
    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def call(self, *args, **kwargs):
        """
        Execute when an emergency condition is detected.

        :return: Tuple of (event_name, data_dict)
        """
        event_name = "EmergencyEvent"
        data = {"message": self.message}
        logger.info(f"Event generated: {event_name} with message {self.message}")
        return event_name, data


async def check_emergency_detection_function(request: Request):
    """
    Asynchronous function to check for emergencies based on incoming data.

    :param request: FastAPI Request object containing JSON data.
    :return: JSON response with the status of the operation.
    """
    logger.info("check_emergency_detection_function invoked.")
    try:
        data = await request.json()
        logger.info(f"Received data: {data}")

        # Load room stats (model) from MinIO
        room_stats = load_model_from_minio()
        if not room_stats:
            raise RuntimeError("Failed to load model from MinIO.")

        # Fetch sensor data and prepare it for the model
        sensor_data = fetch_all_sensor_data(
            start_hours=FETCH_START_HOURS, 
            interval_hours=FETCH_INTERVAL_HOURS
        )
        if not sensor_data:
            logger.warning("No sensor data retrieved from 'fetch_all_sensor_data'.")
            return {"status": "no_data", "message": "No sensor data retrieved."}

        prepared_df = prepare_data_for_detection(sensor_data)

        if prepared_df.empty:
            logger.warning("Data preparation resulted in an empty DataFrame.")
            return {"status": "no_data", "message": "Data preparation resulted in an empty DataFrame."}

        # Detect potential emergencies
        emergency_detected, message = detect_emergency(prepared_df, room_stats)
        if emergency_detected:
            logger.info(f"Emergency detected: {message}")
            trigger = OneShotTrigger(EmergencyEvent(message))
            trigger.call()
        else:
            logger.info("No emergency detected.")

        return {"status": "success"}

    except ValueError as ve:
        logger.error(f"ValueError in check_emergency_detection_function: {ve}", exc_info=True)
        return {"status": "error", "message": str(ve)}
    except RuntimeError as re:
        logger.error(f"RuntimeError in check_emergency_detection_function: {re}", exc_info=True)
        return {"status": "error", "message": str(re)}
    except Exception as e:
        logger.error(f"Unexpected error in check_emergency_detection_function: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


# Instantiate events
train_occupancy_model_event = TrainOccupancyModelEvent()
check_emergency_event = CheckEmergencyEvent()

# Create periodic triggers
periodic_trigger_train_model = PeriodicTrigger(
    train_occupancy_model_event,
    duration=TRAIN_MODEL_INTERVAL,
    wait_time=TRAIN_MODEL_WAIT_TIME
)
logger.info("Periodic trigger for TrainOccupancyModelEvent configured.")

periodic_trigger_check_emergency = PeriodicTrigger(
    check_emergency_event,
    duration=CHECK_EMERGENCY_INTERVAL,
    wait_time=CHECK_EMERGENCY_WAIT_TIME
)
logger.info("Periodic trigger for CheckEmergencyEvent configured.")

# Initialize gateway
app = LocalGateway()
logger.info("Gateway initialized.")

# Deploy the emergency detection function
app.deploy(
    check_emergency_detection_function,
    name="check_emergency_detection_function",
    evts="CheckEmergencyEvent",
    method="POST"
)
logger.info("check_emergency_detection_function deployed.")