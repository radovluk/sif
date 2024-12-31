import logging
import pandas as pd
from sklearn.preprocessing import LabelEncoder

base_logger = logging.getLogger(__name__)

def prepare_data_for_occupancy_model(sensor_data: list) -> pd.DataFrame:
    """
    Prepare sensor data for model training.
    """
    df = pd.DataFrame(sensor_data)
    base_logger.info(f"Original data shape: {df.shape}")

    # Handle 'sensor' as a list
    if 'sensor' in df.columns:
        df['sensor'] = df['sensor'].apply(
            lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 'unknown_sensor'
        )

    # Convert timestamp to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    # Sort by timestamp
    df = df.sort_values('timestamp')

    # Encode 'sensor'
    if 'sensor' in df.columns:
        le = LabelEncoder()
        try:
            df['sensor_encoded'] = le.fit_transform(df['sensor'])
        except Exception as e:
            base_logger.error(f"Error encoding 'sensor': {e}")
            df['sensor_encoded'] = 0  # fallback

    return df


def train_occupancy_model(sensor_data_df: pd.DataFrame) -> pd.DataFrame:
    """
    Train model by computing mean & std of durations per 'value' (room).
    """
    # Detect changes in room
    sensor_data_df['room_change'] = (sensor_data_df['value'] != sensor_data_df['value'].shift(1)).astype(int)

    # Create a cumulative sum to assign group IDs
    sensor_data_df['group_id'] = sensor_data_df['room_change'].cumsum()

    # Group and compute start/end times
    duration_df = sensor_data_df.groupby(['group_id', 'value']).agg(
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max')
    ).reset_index()

    # Calculate durations
    duration_df['duration'] = duration_df['end_time'] - duration_df['start_time']
    duration_df['duration_seconds'] = duration_df['duration'].apply(lambda x: pd.to_timedelta(x).total_seconds())

    # Group by 'value' to get mean & std
    room_stats = duration_df.groupby('value')['duration_seconds'].agg(['mean', 'std']).reset_index()
    room_stats['std'] = room_stats['std'].fillna(0)

    return room_stats
