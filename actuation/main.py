from base import LocalGateway, base_logger, PeriodicTrigger, BaseEventFabric
from fastapi import Request
import json
import urllib3
import time

VIZ_COMPONENT_URL = "http://192.168.81.143:9000"

def send_todo(title, message, level):
    # Generate the current Unix timestamp in milliseconds
    current_timestamp = int(time.time() * 1000)

    # Serialize the message object to a JSON-formatted string
    try:
        # If 'message' is a dictionary or a serializable object
        serialized_message = json.dumps(message)
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to serialize 'message': {e}")
        # Fallback to string conversion if serialization fails
        serialized_message = str(message)

    # Create the ToDo item
    todo_item = {
        "timestamp": current_timestamp,
        "titel": title,
        "msg": serialized_message,
        "level": level
    }

    # Convert the Python dictionary to a JSON string
    encoded_data = json.dumps(todo_item).encode('utf-8')

    # Initialize the PoolManager
    http = urllib3.PoolManager()

    # Define the URL
    url = f"{VIZ_COMPONENT_URL}/api/todo"

    # Set the headers
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        # Send the POST request
        response = http.request(
            'POST',
            url,
            body=encoded_data,
            headers=headers
        )
        
        # Check the response status
        if response.status in [200, 201]:
            print("ToDo item saved successfully.")
            # Optionally, parse the response data
            if response.data:
                response_data = json.loads(response.data.decode('utf-8'))
                print("Response:", response_data)
        else:
            print(f"Failed to save ToDo item. Status Code: {response.status}")
            print("Response:", response.data.decode('utf-8'))
    except urllib3.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

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