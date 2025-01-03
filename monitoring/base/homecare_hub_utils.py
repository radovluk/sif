import json
import logging
import time
import urllib3
from config import VIZ_COMPONENT_URL

logger = logging.getLogger(__name__)

def send_info(summary: str, detail: str, level: int) -> None:
    """
    Sends an informational item to the /api/info endpoint of the VIZ component.

    :param summary: Short description or summary of the information.
    :param detail: Detailed information (any serializable object).
    :param level: Priority or level of the information.
    """
    current_timestamp = int(time.time() * 1000)

    info_item = {
        "timestamp": current_timestamp,
        "summary": summary,
        "detail": detail,
        "level": level
    }

    # Encode the info_item to JSON bytes
    try:
        encoded_data = json.dumps(info_item).encode('utf-8')
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to encode info item to JSON: {e}")
        return

    http = urllib3.PoolManager()
    url = f"{VIZ_COMPONENT_URL}/api/info"
    headers = {"Content-Type": "application/json"}

    try:
        response = http.request("POST", url, body=encoded_data, headers=headers)
        if response.status in [200, 201]:
            logger.info("Information item saved successfully.")
            if response.data:
                # Attempt to parse the response as JSON
                try:
                    response_data = json.loads(response.data.decode("utf-8"))
                    logger.info(f"Response: {response_data}")
                except json.JSONDecodeError:
                    logger.warning("Response data is not valid JSON.")
        else:
            logger.error(f"Failed to save info. HTTP Status: {response.status}")
            logger.error(f"Response: {response.data.decode('utf-8')}")
    except urllib3.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


def send_todo(title: str, message: str, level: int) -> None:
    """
    Sends a ToDo item to the /api/todo endpoint of the VIZ component.

    :param title: Title of the ToDo item.
    :param message: Detailed message (any JSON-serializable object).
    :param level: Priority or level of the ToDo item.
    """
    # Generate the current Unix timestamp in milliseconds
    current_timestamp = int(time.time() * 1000)

    # Create the ToDo item
    todo_item = {
        "timestamp": current_timestamp,
        "titel": title,
        "msg": message,
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