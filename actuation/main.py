from base import LocalGateway, base_logger
from base.homecare_hub_utils import send_todo
from fastapi import Request

# Initialize the LocalGateway application
app = LocalGateway()
base_logger.info("Gateway initiated.")

# Define an asynchronous function to handle emergency notifications
async def create_emergency_notification_function(request: Request):
    base_logger.info("Function create emergency notification called.")
    msg = await request.json()  # Parse the incoming JSON request
    base_logger.info(f"Function create_emergency_notification_function received data: {msg}")
    base_logger.info("Now I will send the emergency Notification.")
    send_todo("🚨 Patient Emergency! 🚨", msg, 2)  # Send the emergency notification
    return {"status": "success"}

# Define an asynchronous function to handle burglary notifications
async def create_burglary_notification_function(request: Request):
    base_logger.info("Function create burglary notification called.")
    msg = await request.json()  # Parse the incoming JSON request
    base_logger.info(f"Function create_burglary_notification_function received data: {msg}")
    base_logger.info("Now I will send the burglary Notification.")
    send_todo("🏠🚔 Burglary Alert! 🏠🔐", msg, 2)  # Send the burglary notification
    return {"status": "success"}

# Deploy the emergency notification function
app.deploy(
    create_emergency_notification_function, 
    name="create_emergency_notification_function", 
    evts="EmergencyEvent", 
    method="POST"
)
base_logger.info("create_emergency_notification_function app deployed.")

# Deploy the burglary notification function
app.deploy(
    create_burglary_notification_function, 
    name="create_burglary_notification_function", 
    evts="BurglaryEvent", 
    method="POST"
)
base_logger.info("create_burglary_notification_function app deployed.")