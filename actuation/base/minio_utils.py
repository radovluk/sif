# minio_utils.py

import logging
import json
from io import BytesIO, StringIO
from datetime import datetime
import pandas as pd
from minio import Minio
from minio.error import S3Error
from typing import Optional

from config import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_BUCKET,
    MINIO_OBJECT_NAME_PREFIX,
    LATEST_POINTER_FILE
)

base_logger = logging.getLogger(__name__)


def initialize_minio_client() -> Optional[Minio]:
    """
    Initialize and return a MinIO client.
    """
    try:
        client = Minio(
            endpoint=MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )
        base_logger.info("Initialized MinIO client successfully.")
        return client
    except Exception as e:
        base_logger.error(f"Error initializing MinIO client: {e}")
        return None


def save_model_to_minio(room_stats: pd.DataFrame, model_type: str) -> None:
    """
    Save the room statistics model (pandas DataFrame) to MinIO,
    keeping the last two versions and updating a model-specific pointer file.

    :param room_stats: The DataFrame containing model stats (mean, std, etc.).
    :param model_type: A string identifying the model type, e.g. 'occupancy' or 'motion'.
    """
    model_json = room_stats.to_json(orient='records', date_format='iso')

    client = initialize_minio_client()
    if client is None:
        base_logger.error("Failed to initialize MinIO client. Model not saved.")
        return

    # Ensure the bucket exists
    try:
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
            base_logger.info(f"Bucket '{MINIO_BUCKET}' created.")
        else:
            base_logger.info(f"Bucket '{MINIO_BUCKET}' already exists.")
    except S3Error as e:
        base_logger.error(f"Error checking/creating bucket '{MINIO_BUCKET}': {e}")
        return

    # Incorporate model_type into object_name
    timestamp_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    object_name = f"{MINIO_OBJECT_NAME_PREFIX}_{model_type}_{timestamp_str}.json"

    try:
        data = model_json.encode('utf-8')
        data_stream = BytesIO(data)
        data_length = len(data)

        # Upload the JSON data
        client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            data=data_stream,
            length=data_length,
            content_type='application/json'
        )
        base_logger.info(f"[{model_type.upper()} MODEL] Saved to MinIO as '{object_name}' in bucket '{MINIO_BUCKET}'.")

        # Define the pointer file name
        pointer_file = f"latest_{model_type}.json"

        # Initialize pointers
        latest = object_name
        second_latest = None

        # Try to read existing pointers
        try:
            response = client.get_object(
                bucket_name=MINIO_BUCKET,
                object_name=pointer_file
            )
            pointer_data = response.read().decode('utf-8')
            response.close()
            response.release_conn()

            pointers = json.loads(pointer_data)
            previous_latest = pointers.get("latest")
            previous_second_latest = pointers.get("second_latest")

            # Update pointers
            second_latest = previous_latest  # The current latest becomes second_latest
            if previous_second_latest:
                # Optionally delete the older model beyond the second_latest
                client.remove_object(MINIO_BUCKET, previous_second_latest)
                base_logger.info(f"[{model_type.upper()} MODEL] Removed older model '{previous_second_latest}' from bucket.")

        except S3Error as e:
            # Pointer file does not exist yet
            base_logger.info(f"[{model_type.upper()} MODEL] Pointer file '{pointer_file}' does not exist. Creating new pointer.")
        except json.JSONDecodeError as e:
            base_logger.error(f"[{model_type.upper()} MODEL] Error decoding pointer file '{pointer_file}': {e}")

        # Prepare the new pointer data
        new_pointers = {
            "latest": latest,
            "second_latest": second_latest
        }
        pointer_json = json.dumps(new_pointers).encode('utf-8')
        pointer_stream = BytesIO(pointer_json)

        # Upload the updated pointer file
        client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=pointer_file,
            data=pointer_stream,
            length=len(pointer_json),
            content_type='application/json'
        )
        base_logger.info(f"[{model_type.upper()} MODEL] Pointer file '{pointer_file}' updated.")

    except S3Error as e:
        base_logger.error(f"[{model_type.upper()} MODEL] Error uploading model to MinIO: {e}")

def load_model_from_minio(model_type: str, version: int = 1) -> Optional[pd.DataFrame]:
    """
    Load the latest or second-to-last model statistics DataFrame from MinIO by reading a model-specific pointer file.

    :param model_type: A string identifying the model type, e.g. 'occupancy' or 'motion'.
    :param version: An integer specifying which version to load (1 for latest, 2 for second-to-last).
                    Defaults to 1.
    :return: A pandas DataFrame with the model statistics, or None on error.
    """
    if version not in [1, 2]:
        base_logger.error("Invalid version specified. Use 1 for latest or 2 for second-to-last.")
        return None

    client = initialize_minio_client()
    if client is None:
        base_logger.error("Failed to initialize MinIO client. Model not loaded.")
        return None

    # Define the pointer file name
    pointer_file = f"latest_{model_type}.json"
    try:
        response = client.get_object(
            bucket_name=MINIO_BUCKET,
            object_name=pointer_file
        )
        pointer_data = response.read().decode('utf-8')
        response.close()
        response.release_conn()

        pointers = json.loads(pointer_data)
        if version == 1:
            target_object = pointers.get("latest")
        elif version == 2:
            target_object = pointers.get("second_latest")

        if not target_object:
            base_logger.error(f"[{model_type.upper()} MODEL] No model found for version {version}.")
            return None

        base_logger.info(f"[{model_type.upper()} MODEL] Loading model '{target_object}' (version {version}).")

    except S3Error as e:
        base_logger.error(f"[{model_type.upper()} MODEL] Error reading pointer file '{pointer_file}': {e}")
        return None
    except json.JSONDecodeError as e:
        base_logger.error(f"[{model_type.upper()} MODEL] Error decoding pointer file '{pointer_file}': {e}")
        return None

    # Download the target model object
    try:
        response = client.get_object(
            bucket_name=MINIO_BUCKET,
            object_name=target_object
        )
        data = response.read()
        response.close()
        response.release_conn()
        base_logger.info(f"[{model_type.upper()} MODEL] '{target_object}' downloaded.")
    except S3Error as e:
        base_logger.error(f"[{model_type.upper()} MODEL] Error downloading model '{target_object}': {e}")
        return None

    # Deserialize JSON to DataFrame
    try:
        model_json = data.decode('utf-8')
        room_stats = pd.read_json(StringIO(model_json), orient='records')
        base_logger.info(f"[{model_type.upper()} MODEL] Model deserialized successfully.")
        return room_stats
    except Exception as e:
        base_logger.error(f"[{model_type.upper()} MODEL] Error deserializing model JSON: {e}")
        return None
