from base import LocalGateway, base_logger, PeriodicTrigger, BaseEventFabric
from fastapi import Request
import json

app = LocalGateway()
base_logger.info("Gateway initiated.")

async def create_emergency_notification_function(request: Request):
    base_logger.info("Function create emergency notification called.")
    data = await request.json()
    base_logger.info(f"Function create_occupancy_model_function received data: {data}")
    base_logger.info("Now I will send the emergency email.")
    # TODO send the emergency email
    return {"status": "success"}

app.deploy(
    create_emergency_notification_function, 
    name="create_emergency_notification_function", 
    evts="EmergencyEvent", 
    method="POST"
)

base_logger.info("create_emergency_notification_function app deployed.")