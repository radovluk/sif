from base import LocalGateway, base_logger, PeriodicTrigger, BaseEventFabric
from base.homecare_hub_utils import send_info, send_todo
from fastapi import Request
import json
import urllib3
import time

app = LocalGateway()
base_logger.info("Gateway initiated.")

async def create_emergency_notification_function(request: Request):
    base_logger.info("Function create emergency notification called.")
    mgs = await request.json()
    base_logger.info(f"Function create_occupancy_model_function received data: {mgs}")
    base_logger.info("Now I will send the emergency Notification.")
    send_todo("Emergency event created.", mgs, 2)
    return {"status": "success"}

app.deploy(
    create_emergency_notification_function, 
    name="create_emergency_notification_function", 
    evts="EmergencyEvent", 
    method="POST"
)

base_logger.info("create_emergency_notification_function app deployed.")