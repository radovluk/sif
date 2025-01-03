import logging
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
from io import BytesIO, StringIO

import pandas as pd
from sklearn.preprocessing import LabelEncoder
from minio import Minio, S3Error  # Ensure MinIO client is imported

from base.influx_utils import fetch_all_sensor_data
from base.minio_utils import load_model_from_minio

# ------------------------------
# Constants
# ------------------------------
THRESHOLD_FOR_EMERGENCY_DETECTION = 3  # Number of standard deviations to trigger an emergency
DOOR_OPEN_EVENT = 'livingroom_door_open'
UNKNOWN_ROOM = 'unknown_room'


# ------------------------------
# Logging Configuration
# ------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S'
)
base_logger = logging.getLogger(__name__)

# ------------------------------
# Helper Functions
# ------------------------------

def map_sensor_to_room(sensor_name: str) -> str:
    """
    Map sensor names to a 'room' or event label.

    :param sensor_name: The name of the sensor.
    :return: The corresponding room or event label.
    """
    sensor_mapping = {
        'bathroom_PIR': 'bathroom',
        'kitchen_PIR': 'kitchen',
        'livingroom_PIR': 'livingroom',
        'livingroom_magnetic_switch': DOOR_OPEN_EVENT
    }
    return sensor_mapping.get(sensor_name, UNKNOWN_ROOM)


def prepare_data_for_occupancy_model(sensor_data: List[dict]) -> pd.DataFrame:
    """
    Prepare sensor data for occupancy model training.

    This includes:
      - Converting the list of sensor data dictionaries to a DataFrame.
      - Handling cases where 'sensor' is a list.
      - Converting timestamps from milliseconds to datetime.
      - Sorting the DataFrame by timestamp.
      - Encoding the 'sensor' column.

    :param sensor_data: A list of dictionaries containing sensor readings.
    :return: A pandas DataFrame with time-sorted and label-encoded sensor data.
    """
    df = pd.DataFrame(sensor_data)
    base_logger.info(f"Original data shape: {df.shape}")

    # Handle 'sensor' as a list
    if 'sensor' in df.columns:
        df['sensor'] = df['sensor'].apply(
            lambda x: x[0] if isinstance(x, list) and len(x) > 0 else UNKNOWN_ROOM
        )
        base_logger.info("Handled 'sensor' as a list.")
    else:
        base_logger.warning("'sensor' column not found in sensor data.")

    # Convert timestamp from milliseconds to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        base_logger.info("Timestamps converted to datetime.")
    else:
        base_logger.warning("'timestamp' column not found in sensor data.")

    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)
    base_logger.info("Data sorted by timestamp.")

    # Encode 'sensor' (optional)
    if 'sensor' in df.columns:
        le = LabelEncoder()
        try:
            df['sensor_encoded'] = le.fit_transform(df['sensor'])
            base_logger.info("Sensor names encoded successfully.")
        except Exception as e:
            base_logger.error(f"Error encoding 'sensor': {e}")
            df['sensor_encoded'] = 0  # Fallback encoding
            base_logger.info("Fallback encoding applied to 'sensor'.")

    return df


def calculate_times_in_each_room(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate the duration of time spent in each 'sensor' event or 'room'.

    This function:
      - Maps each sensor to a room or event label.
      - Identifies room-change points.
      - Groups consecutive events in the same room.
      - Calculates start and end times, durations, and duration in seconds.
      - Excludes all door-opening events from the final DataFrame.

    :param df: A pandas DataFrame with at least 'timestamp' and 'sensor' columns.
    :return: A DataFrame containing start_time, end_time, duration, duration_seconds for each group.
    """
    df = df.copy()

    # Map each sensor to a room/event label
    df['room'] = df['sensor'].apply(map_sensor_to_room)
    base_logger.info("Mapped sensors to rooms.")

    # Identify room-change points
    df['room_change'] = (df['room'] != df['room'].shift(1)).astype(int)
    df['group_id'] = df['room_change'].cumsum()
    base_logger.info("Identified room-change points and assigned group IDs.")

    # Calculate start/end times for each group
    duration_df = df.groupby(['group_id', 'room'], as_index=False).agg(
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max')
    )
    base_logger.info("Calculated start and end times for each group.")

    # Compute durations
    duration_df['duration'] = duration_df['end_time'] - duration_df['start_time']
    duration_df['duration_seconds'] = duration_df['duration'].dt.total_seconds()
    base_logger.info("Computed durations for each group.")

    # Exclude all door-opening events
    initial_count = len(duration_df)
    duration_df = duration_df[duration_df['room'] != DOOR_OPEN_EVENT].reset_index(drop=True)
    excluded_count = initial_count - len(duration_df)
    if excluded_count > 0:
        base_logger.info(f"Excluded {excluded_count} door-opening event(s) from the final DataFrame.")

    return duration_df


def prepare_data_for_detection(sensor_data: List[dict]) -> pd.DataFrame:
    """
    Full preparation pipeline for emergency detection.

    This includes:
      1. Preparing sensor data for occupancy modeling (sorting, encoding).
      2. Calculating durations of time spent in each room.

    :param sensor_data: A list of raw sensor data dictionaries.
    :return: A DataFrame with columns: ['room', 'start_time', 'end_time', 'duration', 'duration_seconds'].
    """
    base_logger.info("Starting data preparation for detection.")
    df_prepared = prepare_data_for_occupancy_model(sensor_data)
    duration_df = calculate_times_in_each_room(df_prepared)
    base_logger.info("Data preparation for detection completed.")
    return duration_df


def format_duration(seconds: float) -> str:
    """
    Convert seconds to a formatted string HH:MM:SS.

    :param seconds: Duration in seconds.
    :return: Formatted duration string.
    """
    return str(timedelta(seconds=int(round(seconds))))


def retrieve_patient_location(sensor_data: List[dict]) -> Tuple[str, float]:
    """
    Retrieve the current room and the duration spent in that room by the patient.

    :param sensor_data: A list of raw sensor data dictionaries.
    :return: A tuple containing the current room and duration in seconds.
    """
    base_logger.info("Retrieving patient location and duration.")
    duration_df = prepare_data_for_detection(sensor_data)

    if duration_df.empty:
        base_logger.warning("No room-duration records available to determine patient location.")
        return UNKNOWN_ROOM, 0.0

    last_record = duration_df.iloc[-1]
    room = last_record["room"]
    duration = last_record["duration_seconds"]

    base_logger.info(f"Patient is currently in '{room}' for {duration:.2f} seconds.")
    return room, duration


def retrieve_room_stats(model_type: str = "occupancy") -> Optional[pd.DataFrame]:
    """
    Retrieve room statistics (mean and standard deviation) for the specified model type.

    :param model_type: The type of model (e.g., 'occupancy', 'motion').
    :return: A pandas DataFrame with room statistics or None if loading fails.
    """
    base_logger.info(f"Retrieving room stats for model type '{model_type}'.")
    room_stats = load_model_from_minio(model_type)
    if room_stats is None or room_stats.empty:
        base_logger.error(f"Failed to load '{model_type}' model from MinIO.")
        return None
    base_logger.info(f"Loaded '{model_type}' room statistics from MinIO.")
    return room_stats


def detect_emergency(room: str, duration: float, stats: pd.Series, threshold: int = THRESHOLD_FOR_EMERGENCY_DETECTION) -> Tuple[bool, str]:
    """
    Detects an emergency based on the room, duration spent in the room, and room statistics.

    :param room: The current room where the patient is located.
    :param duration: The duration spent in the current room (in seconds).
    :param stats: A pandas Series containing 'mean' and 'std' for the room.
    :param threshold: The number of standard deviations away from the mean to trigger an emergency.
    :return: A tuple (emergency_detected, message).
    """
    if room == DOOR_OPEN_EVENT:
        info_message = "🚪 Living room door opening event detected. Not considered for emergency detection."
        base_logger.info(info_message)
        return False, info_message

    mean = stats.get("mean", 0)
    std = stats.get("std", 0)

    base_logger.info(f"Room '{room}' stats - Mean: {mean:.2f} seconds, Std: {std:.2f} seconds.")

    if std == 0:
        # If std is zero, any deviation from mean is unusual
        if duration != mean:
            emergency_message = (
                f"🚨 Emergency Alert! 🚨\n "
                f"Room: {room}.\n "
                f"Patient has spent {format_duration(duration)} here.\n "
                f"Expected duration (mean): {format_duration(mean)},\n "
                f"Standard deviation (std): {format_duration(std)},\n "
                f"Duration is outside the expected value with no variability allowed."
            )
            base_logger.warning(emergency_message)
            return True, emergency_message
        else:
            no_emergency_message = (
                f"✅ All is well! ✅\n "
                f"Patient is currently in {room} for {format_duration(duration)}.\n "
                f"No emergency detected.\n "
                f"Expected duration matches the recorded duration: {format_duration(mean)}."
            )
            base_logger.info(no_emergency_message)
            return False, no_emergency_message
    else:
        lower_bound = mean - threshold * std
        lower_bound = max(lower_bound, 0)  # Ensure lower_bound is not negative
        upper_bound = mean + threshold * std

        base_logger.info(
            f"Duration bounds for emergency detection: ({lower_bound:.2f}, {upper_bound:.2f}) seconds."
        )

        if duration < lower_bound or duration > upper_bound:
            emergency_message = (
                f"🚨 Emergency Alert! 🚨\n "
                f"Room: {room},\n "
                f"Patient has spent {format_duration(duration)} here.\n "
                f"Expected duration (mean): {format_duration(mean)},\n "
                f"Standard deviation (std): {format_duration(std)},\n "
                f"Threshold used: {threshold},\n "
                f"Allowed duration range: {format_duration(lower_bound)} - {format_duration(upper_bound)},\n"
                f"Duration is outside the allowed range!"
            )
            base_logger.warning(emergency_message)
            return True, emergency_message
        else:
            no_emergency_message = (
                f"✅ All is well! ✅\n "
                f"Patient is currently in {room} for {format_duration(duration)}.\n "
                f"No emergency detected.\n "
                f"Expected duration (mean): {format_duration(mean)},\n "
                f"Standard deviation (std): {format_duration(std)},\n "
                f"Allowed duration range: {format_duration(lower_bound)} - {format_duration(upper_bound)}."
            )
            base_logger.info(no_emergency_message)
            return False, no_emergency_message


def emergency_detection_workflow(threshold: int = THRESHOLD_FOR_EMERGENCY_DETECTION) -> Tuple[bool, str]:
    """
    The main workflow to detect emergencies. It orchestrates data retrieval, processing, and emergency detection.

    :param threshold: The number of standard deviations away from the mean to trigger an emergency.
    :return: A tuple (emergency_detected, message).
    """
    base_logger.info("Initiating emergency detection workflow.")

    # Retrieve sensor data
    sensor_data = fetch_all_sensor_data(
        start_hours=24,
        interval_hours=24
    )
    if not sensor_data:
        warning_message = "No sensor data retrieved from 'fetch_all_sensor_data'."
        base_logger.warning(warning_message)
        return False, warning_message

    base_logger.info(f"Fetched {len(sensor_data)} sensor data records.")

    # Retrieve patient location and duration
    room, duration = retrieve_patient_location(sensor_data)
    if room == UNKNOWN_ROOM:
        warning_message = "Unable to determine patient's current location."
        base_logger.warning(warning_message)
        return False, warning_message

    # Retrieve room statistics
    room_stats_df = retrieve_room_stats("occupancy")
    if room_stats_df is None or room_stats_df.empty:
        error_message = "Room statistics not available for emergency detection."
        base_logger.error(error_message)
        return False, error_message

    # Get stats for the current room
    stats = room_stats_df[room_stats_df["room"] == room]
    if stats.empty:
        error_message = f"No stats found for room '{room}'. Cannot detect emergency."
        base_logger.error(error_message)
        return False, error_message

    stats_series = stats.iloc[0]

    # Detect emergency
    emergency_detected, message = detect_emergency(room, duration, stats_series, threshold)

    base_logger.info("Emergency detection workflow completed.")
    return emergency_detected, message
            
def detect_burglary() -> Tuple[bool, str]:
    """
    Detects an burglary based on fetched sensor data and room statistics.
    
    :return: A tuple (emergency_detected, message).

    # TODO implement this function:

    Final Assignment

    Implement an additional use case for the Digital Twin. 
    One possibility is a path analysis. 

    1. Determine paths taken in the apartment. A path is the sequence of rooms visited during an hour. For example, you have the following events: 
    7:58 kitchen, 8:05 bathroom, 8:20 living room, 8:30 kitchen, 9:10 Living room. 
    This will a path kitchen->bathroom->living room->kitchen from 8:00 to 09:00 and one Kitchen->living room from 09:00-10:00. 
    You can also use another definition of path, e.g., that it ends if you stay longer than 15 minutes in a room. 

    2. Implement an analysis for behavioral changes based on the paths and visualize the results. 
    Alternative: You develop your own use case, which need not be related to Senior Homecare but is based on the collected room events. You could, for example, use a ML model to predict the next room to be visited and report anomalies in case it is different. 
    """
    base_logger.info(f"Function detect_burglary() called.")
    return True, "Burlgary detected, disclaimer: Not implemented yet"
