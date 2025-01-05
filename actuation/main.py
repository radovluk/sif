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
    msg = await request.json()
    base_logger.info(f"Function create_emergency_notification_function received data: {msg}")
    base_logger.info("Now I will send the emergency Notification.")
    send_todo("🚨 Patient Emergency! 🚨", msg, 2)
    return {"status": "success"}

async def create_burglary_notification_function(request: Request):
    base_logger.info("Function create burglary notification called.")
    msg = await request.json()
    base_logger.info(f"Function create_burglary_notification_function received data: {msg}")
    base_logger.info("Now I will send the burglary Notification.")
    send_todo("🏠🚔 Burglary Alert! 🏠🔐", msg, 2)
    return {"status": "success"}

app.deploy(
    create_emergency_notification_function, 
    name="create_emergency_notification_function", 
    evts="EmergencyEvent", 
    method="POST"
)
base_logger.info("create_emergency_notification_function app deployed.")

app.deploy(
    create_burglary_notification_function, 
    name="create_emergency_notification_function", 
    evts="BurglaryEvent", 
    method="POST"
)
base_logger.info("create_burglary_notification_function app deployed.")