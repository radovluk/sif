from base import LocalGateway, base_logger, PeriodicTrigger, BaseEventFabric, OneShotTrigger
from fastapi import Request
import json

class TrainOccupancyModelEvent(BaseEventFabric):
    def __init__(self):
        super(TrainOccupancyModelEvent, self).__init__()
    
    def call(self, *args, **kwargs):
        evt_name = "TrainOccupancyModelEvent"
        data = {"message": "Now I need to retrain my model"}
        base_logger.info(f"Event generated: {evt_name} with data {data}")
        return evt_name, data

class CheckEmergencyEvent(BaseEventFabric):
    def __init__(self):
        super(CheckEmergencyEvent, self).__init__()
    
    def call(self, *args, **kwargs):
        evt_name = "CheckEmergencyEvent"
        data = {"message": "Now I will check the emergency"}
        base_logger.info(f"Event generated: {evt_name} with data {data}")
        return evt_name, data

class EmergencyEvent(BaseEventFabric):
    def __init__(self):
        super(EmergencyEvent, self).__init__()
    
    def call(self, *args, **kwargs):
        evt_name = "EmergencyEvent"
        data = {"message": "Now I will trigger emergency"}
        base_logger.info(f"Event generated: {evt_name} with data {data}")
        return evt_name, data

async def check_emergency_detection_function(request: Request):
    base_logger.info("Function check emergency called.")
    data = await request.json()
    base_logger.info(f"Function check_emergency_detection_function received data: {data}")
    # TODO check the emergency
    emergency_event = EmergencyEvent()
    base_logger.info("emergency_event instatiated. Calling emergency notification function")
    trigger = OneShotTrigger(emergency_event)
    return {"status": "success"}

# Instantiate the custom event fabric
train_occupancy_model_event = TrainOccupancyModelEvent()
base_logger.info("train_occupancy_model_event instatiated.")

check_emergency_event = CheckEmergencyEvent()
base_logger.info("check_emergency_event instatiated.")

# Create a periodic trigger for the train_occupancy_model_event event
periodicTriggerTrainModel = PeriodicTrigger(
    train_occupancy_model_event,
    duration="30s",
    wait_time="30s"  # Starts after 30s, then triggers every 30 seconds
)
base_logger.info("PeriodicTrigger for train_occupancy_model_event set: Starts after 30s, then triggers every 30 seconds")

# Create a periodic trigger for the check_emergency_event event
periodicTriggerCheckEmergency = PeriodicTrigger(
    check_emergency_event,
    duration="30s",
    wait_time="1m"  # Starts after 1 minute, then triggers every 30 seconds
)
base_logger.info("PeriodicTrigger for check_emergency_event set: Starts after 1 minute, then triggers every 30 seconds")

# Instantiate the LocalGateway
app = LocalGateway()
base_logger.info("Gateway initiated.")

# Deploy the function
app.deploy(check_emergency_detection_function, name="check_emergency_detection_function", evts="CheckEmergencyEvent", method="POST")
base_logger.info("check_emergency_detection_function deployed.")