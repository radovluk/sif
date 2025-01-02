import logging
import pandas as pd
from sklearn.preprocessing import LabelEncoder

base_logger = logging.getLogger(__name__)

def map_sensor_to_room(sensor_name: str) -> str:
    """
    Map sensor names to a 'room' or event label.
    """
    if 'bathroom_PIR' in sensor_name:
        return 'bathroom'
    elif 'kitchen_PIR' in sensor_name:
        return 'kitchen'
    elif 'livingroom_PIR' in sensor_name:
        return 'livingroom'
    elif 'livingroom_magnetic_switch' in sensor_name:
        return 'livingroom_door_open'
    else:
        return 'unknown_room'


def prepare_data_for_occupancy_model(sensor_data: list) -> pd.DataFrame:
    """
    Prepare sensor data for model training.

    :param sensor_data: A list of dictionaries containing sensor readings.
    :return: A pandas DataFrame with time-sorted and label-encoded sensor data.
    """
    df = pd.DataFrame(sensor_data)
    base_logger.info(f"Original data shape: {df.shape}")

    # Handle 'sensor' as a list
    if 'sensor' in df.columns:
        df['sensor'] = df['sensor'].apply(
            lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 'unknown_sensor'
        )

    # Convert timestamp from milliseconds to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    # Sort by timestamp
    df = df.sort_values('timestamp')

    # Encode 'sensor' (optional)
    if 'sensor' in df.columns:
        le = LabelEncoder()
        try:
            df['sensor_encoded'] = le.fit_transform(df['sensor'])
        except Exception as e:
            base_logger.error(f"Error encoding 'sensor': {e}")
            df['sensor_encoded'] = 0  # fallback

    return df


def calculate_times_in_each_room(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate the duration of time spent in each 'sensor' event or 'room'.
    If 'livingroom_magnetic_switch' is triggered, treat it as a separate event (room)
    which causes a change from the previous sensor/room.

    :param df: A pandas DataFrame with at least 'timestamp' and 'sensor' columns.
    :return: A DataFrame containing start_time, end_time, duration, duration_seconds for each group.
    """
    df = df.copy()

    # 1) Map each sensor to a room or event label
    df['room'] = df['sensor'].apply(map_sensor_to_room)

    # 2) Identify room-change points
    df['room_change'] = (df['room'] != df['room'].shift(1)).astype(int)
    df['group_id'] = df['room_change'].cumsum()

    # 3) Calculate start/end times for each group
    duration_df = df.groupby(['group_id', 'room'], as_index=False).agg(
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max')
    )

    # 4) Compute durations
    duration_df['duration'] = duration_df['end_time'] - duration_df['start_time']
    duration_df['duration_seconds'] = duration_df['duration'].dt.total_seconds()

    return duration_df


def train_occupancy_model(sensor_data_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute mean and standard deviation of time spent in each 'room' (including door-open event).

    :param sensor_data_df: A pandas DataFrame with at least 'timestamp' and 'sensor' columns.
    :return: A DataFrame with per-room mean and std of durations.
    """
    # 1) Calculate durations
    duration_df = calculate_times_in_each_room(sensor_data_df)

    # 2) Group by 'room' to get mean & std
    room_stats = duration_df.groupby('room')['duration_seconds'].agg(['mean', 'std']).reset_index()

    # 3) Fill NaNs for std
    room_stats['std'] = room_stats['std'].fillna(0)

    return room_stats