import logging
from fastapi import Request

from base import PeriodicTrigger, OneShotTrigger
from base.gateway import LocalGateway
from base.homecare_hub_utils import send_info
from base.influx_utils import fetch_all_sensor_data
from base.minio_utils import load_model_from_minio
from detection import detect_emergency, prepare_data_for_detection, detect_burglary
from base.event import (
    TrainOccupancyModelEvent,
    CheckEmergencyEvent,
    EmergencyEvent,
    TrainMotionModelEvent,
    AnalyzeMotionEvent,
    TrainBurglaryModelEvent,
    CheckBurglaryEvent,
    BurglaryEvent
)
from config import (
    TRAIN_OCCUPANCY_MODEL_INTERVAL,
    TRAIN_OCCUPANCY_MODEL_WAIT_TIME,
    TRAIN_MOTION_MODEL_INTERVAL,
    TRAIN_MOTION_MODEL_WAIT_TIME,
    CHECK_EMERGENCY_INTERVAL,
    CHECK_EMERGENCY_WAIT_TIME,
    ANALYSE_MOTION_INTERVAL,
    ANALYSE_MOTION_WAIT_TIME,
    TRAIN_BURGLARY_MODEL_INTERVAL,
    TRAIN_BURLGARY_MODEL_WAIT_TIME,
    CHECK_BURGLARY_INTERVAL,
    CHECK_BURGLARY_WAIT_TIME,
    START_HOURS_FOR_EMERGENCY_DETECTION,
    INTERVAL_HOURS_FOR_EMERGENCY_DETECTION
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

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
        if room_stats is None or room_stats.empty:
            raise RuntimeError("Failed to load model from MinIO.")

        # Fetch sensor data and prepare it for the model
        sensor_data = fetch_all_sensor_data(
            start_hours=START_HOURS_FOR_EMERGENCY_DETECTION, 
            interval_hours=INTERVAL_HOURS_FOR_EMERGENCY_DETECTION
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

async def check_burglary_detection_function(request: Request):
    """
    Asynchronous function to check for burglaries based on incoming data.

    :param request: FastAPI Request object containing JSON data.
    :return: JSON response with the status of the operation.
    """
    logger.info("check_burglary_detection_function invoked.")
    try:
        data = await request.json()
        logger.info(f"Received data: {data}")

        # Detect burglary
        burglary_detected, message = detect_burglary()

        if burglary_detected:
            logger.info(f"Burglary detected: {message}")
            trigger = OneShotTrigger(BurglaryEvent(message))
            trigger.call()
        else:
            logger.info("No burglary detected.")

        return {"status": "success"}

# Instantiate events
train_occupancy_model_event = TrainOccupancyModelEvent()
check_emergency_event = CheckEmergencyEvent()
train_motion_model_event = TrainMotionModelEvent()
analyze_motion_event = AnalyzeMotionEvent()
train_burglary_model_event = TrainBurglaryModelEvent()
check_burglary_event = CheckBurglaryEvent()

# Define configurations for events and triggers
events_and_triggers = [
    {
        "event_class": TrainOccupancyModelEvent,
        "trigger_name": "Periodic trigger for TrainOccupancyModelEvent",
        "interval": TRAIN_OCCUPANCY_MODEL_INTERVAL,
        "wait_time": TRAIN_OCCUPANCY_MODEL_WAIT_TIME,
    },
    {
        "event_class": CheckEmergencyEvent,
        "trigger_name": "Periodic trigger for CheckEmergencyEvent",
        "interval": CHECK_EMERGENCY_INTERVAL,
        "wait_time": CHECK_EMERGENCY_WAIT_TIME,
    },
    {
        "event_class": TrainMotionModelEvent,
        "trigger_name": "Periodic trigger for TrainMotionModelEvent",
        "interval": TRAIN_MOTION_MODEL_INTERVAL,
        "wait_time": TRAIN_MOTION_MODEL_WAIT_TIME,
    },
    {
        "event_class": AnalyzeMotionEvent,
        "trigger_name": "Periodic trigger for AnalyzeMotionEvent",
        "interval": ANALYSE_MOTION_INTERVAL,
        "wait_time": ANALYSE_MOTION_WAIT_TIME,
    },
    {
        "event_class": TrainBurglaryModelEvent,
        "trigger_name": "Periodic trigger for TrainBurglaryModelEvent",
        "interval": TRAIN_BURGLARY_MODEL_INTERVAL,
        "wait_time": TRAIN_BURGLARY_MODEL_WAIT_TIME,
    },
    {
        "event_class": CheckBurglaryEvent,
        "trigger_name": "Periodic trigger for CheckBurglaryEvent",
        "interval": CHECK_BURGLARY_INTERVAL,
        "wait_time": CHECK_BURGLARY_WAIT_TIME,
    },
]

# Instantiate events and create periodic triggers
triggers = []
for trigger_config in events_and_triggers:
    event_instance = trigger_config["event_class"]()
    trigger = PeriodicTrigger(
        event_instance,
        duration=trigger_config["interval"],
        wait_time=trigger_config["wait_time"]
    )
    triggers.append(trigger)
    logger.info(f"{trigger_config['trigger_name']} configured.")

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

# Deploy the burglary detection function
app.deploy(
    check_burglary_detection_function,
    name="check_burglary_detection_function",
    evts="CheckBurglaryEvent",
    method="POST"
)
logger.info("check_burglary_detection_function deployed.")