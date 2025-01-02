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
    keeping previous versions and updating a model-specific latest pointer file.

    :param room_stats: The DataFrame containing model stats (mean, std, etc.).
    :param model_type: A string identifying the model type, e.g. 'occupancy' or 'motion'.
    """
    model_json = room_stats.to_json(orient='records', date_format='iso')

    client = initialize_minio_client()
    if client is None:
        base_logger.error("Failed to initialize MinIO client. Model not saved.")
        return

    # Ensure the bucket exists
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)
        base_logger.info(f"Bucket '{MINIO_BUCKET}' created.")
    else:
        base_logger.info(f"Bucket '{MINIO_BUCKET}' already exists.")

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

        # Update a model-specific pointer file, e.g. "latest_occupancy.txt" or "latest_motion.txt"
        pointer_file = f"latest_{model_type}.txt"
        latest_data = object_name.encode('utf-8')
        latest_stream = BytesIO(latest_data)
        client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=pointer_file,
            data=latest_stream,
            length=len(latest_data),
            content_type='text/plain'
        )
        base_logger.info(f"[{model_type.upper()} MODEL] '{pointer_file}' updated to '{object_name}'.")

    except S3Error as e:
        base_logger.error(f"[{model_type.upper()} MODEL] Error uploading model to MinIO: {e}")


def load_model_from_minio(model_type: str) -> Optional[pd.DataFrame]:
    """
    Load the latest model statistics DataFrame from MinIO by reading a model-specific pointer file.
    
    :param model_type: A string identifying the model type, e.g. 'occupancy' or 'motion'.
    :return: A pandas DataFrame with the model statistics, or None on error.
    """
    client = initialize_minio_client()
    if client is None:
        base_logger.error("Failed to initialize MinIO client. Model not loaded.")
        return None

    # Determine which pointer file to read
    pointer_file = f"latest_{model_type}.txt"
    try:
        response = client.get_object(
            bucket_name=MINIO_BUCKET,
            object_name=pointer_file
        )
        latest_object_name = response.read().decode('utf-8').strip()
        response.close()
        response.release_conn()
        base_logger.info(f"[{model_type.upper()} MODEL] Latest object is '{latest_object_name}'.")
    except S3Error as e:
        base_logger.error(f"[{model_type.upper()} MODEL] Error reading '{pointer_file}': {e}")
        return None

    # Download the latest model object
    try:
        response = client.get_object(
            bucket_name=MINIO_BUCKET,
            object_name=latest_object_name
        )
        data = response.read()
        response.close()
        response.release_conn()
        base_logger.info(f"[{model_type.upper()} MODEL] '{latest_object_name}' downloaded.")
    except S3Error as e:
        base_logger.error(f"[{model_type.upper()} MODEL] Error downloading model '{latest_object_name}': {e}")
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
