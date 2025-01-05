import logging
import pandas as pd
from occupancy_model import prepare_data_for_occupancy_model
from base.influx_utils import fetch_all_sensor_data

base_logger = logging.getLogger(__name__)

def data_preprocessing_motion_analysis(df):
    """
    Preprocesses the sensor data by parsing timestamps, identifying value changes,
    and extracting temporal features.

    Parameters:
    - df (pd.DataFrame): The raw sensor DataFrame with columns:
        ['sensor', 'bucket', 'timestamp', 'value', 'type', 'sensor_encoded']

    Returns:
    - pd.DataFrame: A preprocessed DataFrame with grouped events and extracted temporal features.
    """
    # Ensure the 'timestamp' column is in datetime format
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Sort the DataFrame by timestamp to ensure chronological order
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Create a column to identify when 'value' changes
    df['value_change'] = (df['value'] != df['value'].shift(1)).astype(int)

    # Assign a group ID that increments when 'value' changes
    df['group_id'] = df['value_change'].cumsum()

    # Group by 'group_id' and aggregate relevant information
    grouped = df.groupby('group_id').agg(
        value=('value', 'first'),
        sensor=('sensor', 'first'),  # Assuming one sensor per group; adjust if multiple sensors are involved
        enter_time=('timestamp', 'first'),
        leave_time=('timestamp', 'last'),
        count=('timestamp', 'count')
    ).reset_index(drop=True)

    # Calculate duration in seconds between enter and leave times
    grouped['duration_seconds'] = (grouped['leave_time'] - grouped['enter_time']).dt.total_seconds()

    # Extract temporal features from the enter_time
    grouped['week'] = grouped['enter_time'].dt.isocalendar().week
    grouped['day_of_week'] = grouped['enter_time'].dt.dayofweek
    grouped['hour'] = grouped['enter_time'].dt.hour

    # Return the final preprocessed DataFrame with all relevant columns
    return grouped[['value', 'sensor', 'enter_time', 'leave_time', 'duration_seconds', 'count', 'week', 'day_of_week', 'hour']]

def create_transition_dataframe(df, time_threshold_seconds=3600):
    """
    Creates a Transition DataFrame capturing movements between rooms based on consecutive different 'value' entries.
    Also handles special transitions like 'went out' or 'went to sleep' based on time gaps and time of day.
    
    Parameters:
    - df (pd.DataFrame): The preprocessed sensor DataFrame with columns:
        ['value', 'sensor', 'enter_time', 'leave_time', 'duration_seconds', 'count', 'week', 'day_of_week', 'hour']
    - time_threshold_seconds (int): The maximum allowed time difference between transitions to consider as normal movement.
    
    Returns:
    - pd.DataFrame: A Transition DataFrame with columns:
        ['from', 'to', 'transition_time']
    """

    # Handle cases where the DataFrame is empty or has only one record
    if df.empty:
        base_logger.warning("Input DataFrame is empty. No transitions to create.")
        return None
    elif df.shape[0] == 1:
        base_logger.warning("Input DataFrame has only one record. No transitions to create.")
        return None

    # Initialize a list to store transitions
    transitions = []
    
    # Ensure the DataFrame is sorted by 'enter_time'
    df_sorted = df.sort_values('enter_time').reset_index(drop=True)
    
    # Iterate through the DataFrame
    for i in range(len(df_sorted)):
        current_row = df_sorted.iloc[i]
        
        if i > 0:
            previous_row = df_sorted.iloc[i - 1]
            
            # Check if 'value' has changed
            if current_row['value'] != previous_row['value']:
                # Calculate time difference between previous 'leave_time' and current 'enter_time'
                time_diff = (current_row['enter_time'] - previous_row['leave_time']).total_seconds()
                
                # Determine if time difference exceeds the threshold
                if time_diff > time_threshold_seconds:
                    # Determine if it's nighttime based on the hour of the previous 'leave_time'
                    # Nighttime defined as 21:00 (9 PM) to 7:00 (7 AM)
                    hour = previous_row['hour']
                    if 21 <= hour or hour < 7:
                        special_transition = 'went to sleep'
                    else:
                        special_transition = 'went outside'
                    
                    # Add transition from previous room to special transition
                    transitions.append({
                        'from': previous_row['value'],
                        'to': special_transition,
                        'leave_time': previous_row['leave_time'],
                        'enter_time': previous_row['leave_time']
                    })
                    
                    # Add transition from special transition to current room
                    transitions.append({
                        'from': special_transition,
                        'to': current_row['value'],
                        'enter_time': current_row['enter_time'],
                        'leave_time': current_row['enter_time']
                    })
                else:
                    # Normal transition from previous room to current room
                    transitions.append({
                        'from': previous_row['value'],
                        'to': current_row['value'],
                        'leave_time': previous_row['leave_time'],
                        'enter_time': current_row['enter_time']
                    })
    
    # Create the Transition DataFrame
    transition_df = pd.DataFrame(transitions)
    
    # Handle cases where 'from' or 'to' might be missing
    transition_df['from'] = transition_df['from'].fillna('unknown')
    transition_df['to'] = transition_df['to'].fillna('unknown')

    return transition_df

def train_motion_model(start_hours : int = 24 * 7, interval_hours: int = 24 * 7, time_threshold_seconds : int =1800):
    """
    Train the motion model by analyzing sensor data to identify movement patterns between different states.

    The training process involves the following steps:
    1. **Data Retrieval**: Fetch sensor data for a specified time window using the provided `start_hours` and `interval_hours`.
    2. **Data Preparation**: Prepare the fetched data for occupancy modeling.
    3. **Data Preprocessing**: Process the prepared data to analyze motion events and extract relevant features.
    4. **Transition Analysis**: Create a transition DataFrame to capture movements between different motion states.
    5. **Model Storage**: (To be implemented) Store the trained motion model in MinIO with appropriate metadata.

    **Note**: The current implementation returns the transition DataFrame. Future enhancements should include
    training advanced models (e.g., Neural Networks, Markov Chains) and storing them in MinIO.

    Parameters:
    ----------
    start_hours : int, optional
        The number of hours before the current time to start fetching sensor data, by default 168 (7 days).
    interval_hours : int, optional
        The duration in hours for which to fetch sensor data, by default 168 (7 days).
    time_threshold_seconds : int, optional
        The maximum allowed time difference in seconds between consecutive events to consider transitions as normal,
        by default 1800 seconds (30 minutes).
    """
    base_logger.info(f"Fetching sensor data starting {start_hours} hours ago for a duration of {interval_hours} hours.")
    sensor_data = fetch_all_sensor_data(start_hours, interval_hours)
    base_logger.info("Preparing data for occupancy model.")
    df = prepare_data_for_occupancy_model(sensor_data)
    base_logger.info("Preprocessing data for motion analysis.")
    preprocessed_df = data_preprocessing_motion_analysis(df)
    base_logger.info(f"Creating transition DataFrame with a time threshold of {time_threshold_seconds} seconds.")
    transition_df = create_transition_dataframe(preprocessed_df, time_threshold_seconds=time_threshold_seconds)
    base_logger.info(f"Motion model trained.")
    return transition_df