import pandas as pd
from typing import Tuple
from sklearn.preprocessing import LabelEncoder
import logging

base_logger = logging.getLogger(__name__)

def prepare_data_for_detection(sensor_data: list) -> pd.DataFrame:
    """
    Prepare sensor data for model training or inference.
    
    Steps:
      - Convert list of dictionaries to DataFrame.
      - Check for empty DataFrame.
      - Convert timestamp to datetime.
      - Sort by timestamp.
      - Encode 'sensor' category.
      - Create a flag to detect changes in 'value'.
      - Calculate duration of consecutive values.

    :param sensor_data: List of sensor data dictionaries.
    :return: Preprocessed pandas DataFrame, or empty DataFrame if no data.
    """
    # Check if sensor_data is empty
    if not sensor_data:
        base_logger.warning("No sensor data provided. Returning an empty DataFrame.")
        return pd.DataFrame()

    # Convert list of dictionaries to DataFrame
    df = pd.DataFrame(sensor_data)
    base_logger.info(f"Original data shape: {df.shape}")

    # Check if DataFrame is empty
    if df.empty:
        base_logger.warning("DataFrame is empty after conversion from sensor_data.")
        return df

    # Ensure the required columns exist
    required_columns = ["sensor", "timestamp", "value"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        base_logger.error(f"Missing columns in DataFrame: {missing_columns}")
        return pd.DataFrame()  # or handle as needed

    # Convert sensor to a string (if it's a list, pick first element)
    df["sensor"] = df["sensor"].apply(
        lambda x: x[0] if isinstance(x, list) and len(x) > 0 else str(x)
    )
    base_logger.debug("Converted 'sensor' to string if necessary.")

    # Convert timestamp from milliseconds to datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
    base_logger.debug("Converted 'timestamp' to datetime.")

    # Sort by timestamp
    df = df.sort_values("timestamp")

    # Encode categorical variables
    le = LabelEncoder()
    try:
        df["sensor_encoded"] = le.fit_transform(df["sensor"])
        base_logger.debug("Encoded 'sensor' successfully.")
    except Exception as e:
        base_logger.error(f"Error encoding 'sensor' column: {e}")
        df["sensor_encoded"] = 0  # fallback if encoding fails

    # Create a flag that indicates when the 'value' changes compared to the previous row
    df["room_change"] = (df["value"] != df["value"].shift(1)).astype(int)

    # Create a cumulative sum of the 'room_change' flag to assign a unique group ID
    df["group_id"] = df["room_change"].cumsum()

    # Group by 'group_id' and 'value' to handle each consecutive block
    duration_df = df.groupby(["group_id", "value"]).agg(
        start_time=("timestamp", "min"),
        end_time=("timestamp", "max")
    ).reset_index()

    # Calculate duration as the difference between end_time and start_time
    duration_df["duration"] = duration_df["end_time"] - duration_df["start_time"]

    # Convert 'duration' to total seconds
    duration_df["duration_seconds"] = duration_df["duration"].apply(
        lambda x: pd.to_timedelta(x).total_seconds()
    )

    return duration_df


def detect_emergency(fetched_data: pd.DataFrame, room_stats: pd.DataFrame, threshold: int = 3) -> Tuple[bool, str]:
    """
    Detects an emergency based on fetched sensor data and room statistics.

    :param fetched_data: DataFrame containing recent sensor data.
    :param room_stats: DataFrame containing room statistics (mean and std).
    :param threshold: The number of standard deviations away from the mean to trigger an emergency.
    :return: A tuple (emergency_detected, message).
    """
    if fetched_data.empty:
        return False, "No data fetched. Cannot detect emergency."

    last_row = fetched_data.iloc[-1]
    room = last_row['value']
    current_duration = last_row['duration_seconds']

    stats = room_stats[room_stats['value'] == room]
    if stats.empty:
        return False, f"No stats found for room '{room}'. Cannot detect emergency."

    mean = stats['mean'].values[0]
    std = stats['std'].values[0]

    if std == 0:
        if current_duration != mean:
            return True, f"Emergency detected in {room}: duration={current_duration}, mean={mean}, std={std}"
        else:
            return False, f"No emergency in {room}: duration={current_duration} equals mean={mean} (std=0)"
    else:
        lower_bound = mean - threshold * std
        upper_bound = mean + threshold * std

        if current_duration < lower_bound or current_duration > upper_bound:
            return True, (f"Emergency detected in {room}: duration={current_duration}, "
                          f"mean={mean}, std={std}, threshold={threshold}, "
                          f"range=({lower_bound}, {upper_bound})")
        else:
            return False, (f"No emergency in {room}: duration={current_duration} is within "
                           f"mean ± {threshold} * std = ({lower_bound}, {upper_bound})")

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
