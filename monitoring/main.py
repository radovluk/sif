import logging
from fastapi import Request

from base import PeriodicTrigger, OneShotTrigger
from base.gateway import LocalGateway
from patient_emergency_detection import emergency_detection_workflow
from burglary_detection import detect_burglary
from motion_analysis import analyse_motion_patterns

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
    TRESHOLD_FOR_EMERGENCY_DETECTION,
    ANALYSE_MOTION_INTERVAL,
    ANALYSE_MOTION_WAIT_TIME,
    TRAIN_BURGLARY_MODEL_INTERVAL,
    TRAIN_BURGLARY_MODEL_WAIT_TIME,
    CHECK_BURGLARY_INTERVAL,
    CHECK_BURGLARY_WAIT_TIME
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

        # Detect potential emergencies
        emergency_detected, message = emergency_detection_workflow(threshold=TRESHOLD_FOR_EMERGENCY_DETECTION)
        if emergency_detected:
            logger.info(f"Emergency detected: {message}")
            trigger = OneShotTrigger(EmergencyEvent(message))
            # trigger.call()
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
            # trigger.call()
        else:
            logger.info("No burglary detected.")

        return {"status": "success"}
    except ValueError as ve:
        logger.error(f"ValueError in check_burglary_detection_function: {ve}", exc_info=True)
        return {"status": "error", "message": str(ve)}
    except RuntimeError as re:
        logger.error(f"RuntimeError in check_burglary_detection_function: {re}", exc_info=True)
        return {"status": "error", "message": str(re)}
    except Exception as e:
        logger.error(f"Unexpected error in check_burglary_detection_function: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

async def motion_analysis_function(request: Request):
    logger.info("Function motion_analysis_function called.")
    data = await request.json()
    logger.info(f"Received data: {data}")
    analyse_motion_patterns()
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

# List of functions to deploy
functions_to_deploy = [
    {
        "func": check_emergency_detection_function,
        "name": "check_emergency_detection_function",
        "evts": "CheckEmergencyEvent",
        "method": "POST"
    },
    {
        "func": check_burglary_detection_function,
        "name": "check_burglary_detection_function",
        "evts": "CheckBurglaryEvent",
        "method": "POST"
    },
    {
        "func": motion_analysis_function,
        "name": "motion_analysis_function",
        "evts": "AnalyzeMotionEvent",
        "method": "POST"
    }
]

# Initialize gateway
app = LocalGateway()
logger.info("Gateway initialized.")

# Deploy all functions
for func_config in functions_to_deploy:
    app.deploy(
        func_config["func"],
        name=func_config["name"],
        evts=func_config["evts"],
        method=func_config["method"]
    )
    logger.info(f"{func_config['name']} deployed.")