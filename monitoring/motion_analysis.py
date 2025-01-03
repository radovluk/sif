import pandas as pd
from datetime import datetime, timedelta
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import seaborn as sns
import logging
from base.minio_utils import load_model_from_minio
from base.homecare_hub_utils import send_info
import json

# ------------------------------
# Logging Configuration
# ------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S'
)
base_logger = logging.getLogger(__name__)

def detect_wake_up_times(transition_df: pd.DataFrame, transition_state: str = "went to sleep") -> pd.DataFrame:
    """
    Detects the wake-up times from a transition DataFrame.

    Filters the DataFrame for transitions where the 'from' state is "went to sleep"
    and extracts the 'leave_time' as the wake-up time.
    """
    return pd.DataFrame({
        'wake_up_time': transition_df[transition_df['from'] == transition_state]['leave_time']
    })


def detect_went_to_sleep_times(transition_df: pd.DataFrame, transition_state: str = "went to sleep") -> pd.DataFrame:
    """
    Detects the times when the subject went to sleep from a transition DataFrame.

    Filters the DataFrame for transitions where the 'to' state is "went to sleep"
    and extracts the 'leave_time' as the time of going to sleep.
    """
    return pd.DataFrame({
        'went_to_sleep': transition_df[transition_df['to'] == transition_state]['leave_time']
    })


def count_daily_visits(
    transition_df: pd.DataFrame,
    transition_state: str = "bathroom",
    timestamp_col: str = "enter_time"
) -> pd.DataFrame:
    """
    Counts the number of trips to a specified transition state (e.g., 'bathroom') on a daily basis.

    A bathroom trip is identified by a transition where the 'to' column matches the specified state.
    The trip is attributed to the date of the specified timestamp (default is 'enter_time').
    """
    # Drop rows with invalid or missing timestamps
    filtered_df = transition_df.dropna(subset=[timestamp_col]).copy()
    
    # Filter transitions where 'to' matches the transition_state
    trips_df = filtered_df[filtered_df['to'] == transition_state].copy()
    
    # Extract the date from the specified timestamp column
    trips_df['trip_date'] = trips_df[timestamp_col].dt.date
    
    # Count the number of trips per day
    daily_trip_counts = trips_df.groupby('trip_date').size().reset_index(name=f'{transition_state}_trip_count')
    
    # Optionally, sort by date
    daily_trip_counts = daily_trip_counts.sort_values('trip_date').reset_index(drop=True)
    
    return daily_trip_counts

def summary_of_sleep_time_and_time_outside(transition_df):
    df_sleep = make_daily_summary_of_periods(transition_df, "went to sleep")
    df_outside = make_daily_summary_of_periods(transition_df, "went outside")
    # Rename columns
    df_sleep.rename(columns={'total_time': 'sleep_time'}, inplace=True)
    df_outside.rename(columns={'total_time': 'time_outside'}, inplace=True)
    df_sleep['date'] = pd.to_datetime(df_sleep['date'])
    df_outside['date'] = pd.to_datetime(df_outside['date'])
    merged_df = pd.merge(df_sleep, df_outside, on='date', how='outer')
    merged_df['day_of_week'] = merged_df['date'].dt.day_name()
    # Sort by date
    merged_df.sort_values('date', inplace=True)
    # Reorder columns
    merged_df = merged_df[['date', 'day_of_week', 'sleep_time', 'time_outside']]
    merged_df.fillna('0', inplace=True)

    return merged_df

def extract_transition_periods(transition_df: pd.DataFrame, place : str="went to sleep") -> pd.DataFrame:
    """
    Extracts periods from a transition DataFrame based on a specified transition state.
    Place is either "went to sleep" or "went outside".
    """
    df = transition_df[(transition_df['from'] == place) | (transition_df['to'] == place)].copy()

    # Identify Sleep Starts and Sleep Ends
    sleep_starts = df[df['to'] == place].copy()
    sleep_ends = df[df['from'] == place].copy()

    # Ensure that the number of sleep starts and ends are equal
    # If not, handle the discrepancy (e.g., drop the last unmatched sleep start)
    min_length = min(len(sleep_starts), len(sleep_ends))
    sleep_starts = sleep_starts.iloc[:min_length]
    sleep_ends = sleep_ends.iloc[:min_length]

    # Reset indices
    sleep_starts = sleep_starts.reset_index(drop=True)
    sleep_ends = sleep_ends.reset_index(drop=True)

    # Pair each sleep start with the corresponding sleep end
    sleep_periods = pd.DataFrame({
        'start_time': sleep_starts['leave_time'],
        'end_time': sleep_ends['leave_time']
    })

    return sleep_periods

# Function to split sleep duration across days
def split_transition_periods(start, end):
    periods = []
    current = start
    while current.date() < end.date():
        # End of the current day
        end_of_day = datetime.combine(current.date(), datetime.max.time())
        duration = end_of_day - current + timedelta(seconds=1)  # Add 1 second to include the last second
        periods.append({'date': current.date(), 'duration': duration})
        # Move to the start of the next day
        current = datetime.combine(current.date() + timedelta(days=1), datetime.min.time())
    # Last period
    duration = end - current
    periods.append({'date': current.date(), 'duration': duration})
    return periods

def make_daily_summary_of_periods(transition_df: pd.DataFrame, place: str = "went to sleep") -> pd.DataFrame:
    """
    Extracts periods from a transition DataFrame based on a specified transition state.
    Place is either "went to sleep" or "went outside".

    Parameters:
    ----------
    transition_df : pd.DataFrame
        The DataFrame containing transition data with 'start_time' and 'end_time' columns.
    place : str, optional
        The transition state to analyze, by default "went to sleep".

    Returns:
    -------
    pd.DataFrame
        A summary DataFrame containing:
        - 'date': The date of the sleep period.
        - 'total_time': Total sleep duration in hours and minutes.
    """
    sleep_periods = extract_transition_periods(transition_df, place)
    # List to store per-day sleep durations
    sleep_summary = []

    # Iterate over each sleep period and split durations
    for idx, row in sleep_periods.iterrows():
        start = row["start_time"]
        end = row["end_time"]
        if end < start:
            # Handle cases where end is before start (data error)
            continue
        periods = split_transition_periods(start, end)
        for period in periods:
            sleep_summary.append(period)

    # Convert 'duration' to total seconds
    sleep_summary_df = pd.DataFrame(sleep_summary)

    # Handle the case where the DataFrame is empty
    if sleep_summary_df.empty:
        base_logger.warning("No valid sleep periods found.")
        return pd.DataFrame(columns=["date", "total_time"])

    # Ensure the 'duration' column is in timedelta format
    if "duration" in sleep_summary_df.columns:
        sleep_summary_df["duration_seconds"] = sleep_summary_df["duration"].dt.total_seconds()
    else:
        base_logger.error("'duration' column not found in sleep_summary_df.")
        return pd.DataFrame(columns=["date", "total_time"])

    # Aggregate sleep durations by date
    daily_sleep = sleep_summary_df.groupby("date")["duration_seconds"].sum().reset_index()

    # Convert seconds to hours and minutes for readability
    def seconds_to_hours_minutes(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

    daily_sleep["total_time"] = daily_sleep["duration_seconds"].apply(seconds_to_hours_minutes)

    # Optionally, sort by date
    daily_sleep = daily_sleep.sort_values("date").reset_index(drop=True)

    # Display the summary
    return daily_sleep[["date", "total_time"]]


def plot_bidirectional_transaction_graph(df):
    """
    Creates and displays a bidirectional graph based on transaction counts between areas.

    Parameters:
    - df (pd.DataFrame): DataFrame containing 'from', 'to' columns.

    Returns:
    - None
    """
    
    # Aggregate transition counts
    transition_counts = df.groupby(['from', 'to']).size().reset_index(name='count')
    
    # Initialize a directed graph
    G = nx.DiGraph()
    
    # Add edges with weights
    for _, row in transition_counts.iterrows():
        G.add_edge(row['from'], row['to'], weight=row['count'])
    
    # Set the size of the plot
    plt.figure(figsize=(12, 8))
    
    # Use spring layout for better visualization
    pos = nx.spring_layout(G, k=0.5, iterations=50)
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_size=1000, node_color='lightblue')
    
    # Draw labels
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')
    
    # Extract edge weights correctly
    edges = G.edges(data=True)
    weights = [data['weight'] for _, _, data in edges]
    
    # Normalize weights for line thickness
    max_weight = max(weights) if weights else 1  # Avoid division by zero
    widths = [weight / max_weight * 5 for weight in weights]  # Scale widths up to 5
    
    # Draw edges with varying thickness
    nx.draw_networkx_edges(
        G, pos,
        edgelist=G.edges(),
        width=widths,
        arrowstyle='->',
        arrowsize=40,
        edge_color='gray'
    )
    
    # Create a legend for edge weights
    # Define some example weights for the legend
    example_weights = sorted(list(set([1, max_weight//2, max_weight])), reverse=True)
    if max_weight < 2:
        example_weights = [1]
    
    legend_elements = [
        Line2D([0], [0], color='gray', lw=w / max_weight * 5, label=f'{w} transitions')
        for w in example_weights
    ]
    
    plt.legend(handles=legend_elements, title='Edge Weights', loc='upper left')
    
    plt.title('Patient Transaction Graph')
    plt.axis('off')
    plt.tight_layout()
    plt.show()

def visualize_transitions_heatmap(transition_df):
    """
    Visualizes sensor transitions as a heat map.
    
    Parameters:
    - transition_df (pd.DataFrame): The Transition DataFrame with columns:
        ['from', 'to', 'transition_time']
    
    Returns:
    - None
    """
    # Create a pivot table for the heat map
    transition_matrix = transition_df.groupby(['from', 'to']).size().unstack(fill_value=0)
    
    # Create the heat map
    plt.figure(figsize=(10, 8))
    sns.heatmap(
        transition_matrix,
        annot=True,  # Display transition counts
        fmt="d",  # Integer format
        cmap="YlGnBu",  # Color map
        linewidths=0.5,  # Add grid lines
        linecolor="white"  # Grid line color
    )
    
    # Add labels and title
    plt.title('Sensor Transition Heat Map', fontsize=16)
    plt.xlabel('To', fontsize=12)
    plt.ylabel('From', fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.yticks(rotation=0, fontsize=10)
    plt.tight_layout()
    plt.show()


def create_separate_heat_maps(transition_df):
    df = transition_df.copy()
    
    # Define time segments
    def get_time_segment(hour):
        if 6 <= hour < 12:
            return 'Morning'
        elif 12 <= hour < 18:
            return 'Afternoon'
        elif 18 <= hour < 24:
            return 'Evening'
        else:
            return 'Night'
    
    # Extract date, day of week, and time segment
    df['date'] = df['leave_time'].dt.date
    df['day_of_week'] = df['leave_time'].dt.day_name()
    df['time_segment'] = df['leave_time'].dt.hour.apply(get_time_segment)
    
    # Create a mapping from day name to order
    day_order_mapping = {'Monday': 1, 'Tuesday': 2, 'Wednesday': 3, 'Thursday': 4,
                        'Friday': 5, 'Saturday': 6, 'Sunday': 7}
    
    # Add a sort key based on day of week
    df['day_order'] = df['day_of_week'].map(day_order_mapping)
    
    # Sort the DataFrame by day order and leave_time
    df = df.sort_values(by=['day_order', 'leave_time'])
    
    # Get unique dates sorted by day order
    unique_dates = df[['date', 'day_of_week', 'day_order']].drop_duplicates().sort_values('day_order')
    
    # Define the order of time segments
    time_segments_order = ['Morning', 'Afternoon', 'Evening', 'Night']
    
    # Get unique locations for consistent ordering in heatmaps
    locations = sorted(list(set(df['from']).union(set(df['to']))))
    
    # Create pivot tables
    pivot_tables = {}
    for _, row in unique_dates.iterrows():
        date = row['date']
        day = row['day_of_week']
        for segment in time_segments_order:
            subset = df[(df['date'] == date) & (df['time_segment'] == segment)]
            pivot = subset.pivot_table(index='from', columns='to', aggfunc='size', fill_value=0)
            # Reindex to include all locations
            pivot = pivot.reindex(index=locations, columns=locations, fill_value=0)
            pivot_tables[(date, day, segment)] = pivot
    
    # Plot heatmaps without colorbar and with date and day in titles
    plt.figure(figsize=(24, 42))  # Adjust the size as needed
    
    num_days = unique_dates.shape[0]  # Should be 7
    num_segments = len(time_segments_order)
    num_plots = num_days * num_segments
    current_plot = 1
    
    for _, row in unique_dates.iterrows():
        date = row['date']
        day = row['day_of_week']
        for segment in time_segments_order:
            plt.subplot(num_days, num_segments, current_plot)
            sns.heatmap(
                pivot_tables[(date, day, segment)],
                annot=True,
                fmt='d',
                cmap='YlGnBu',
                cbar=False,  # Disable colorbar
                linewidths=.5,
                linecolor='gray'
            )
            # Format the date for display
            formatted_date = pd.to_datetime(date).strftime('%Y-%m-%d')
            plt.title(f"{day}, {formatted_date} - {segment}")
            plt.xlabel('To')
            plt.ylabel('From')
            plt.xticks(rotation=45, ha='right')
            plt.yticks(rotation=0)
            current_plot += 1
    
    plt.tight_layout()
    plt.show()

def format_duration(seconds: float) -> str:
    """
    Formats a duration from seconds to HH:MM:SS format.

    :param seconds: Duration in seconds.
    :return: Formatted duration string.
    """
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}h {minutes}m {secs}s"

def dataframe_to_text(df: pd.DataFrame) -> str:
    """
    Converts a DataFrame to a formatted string with emojis for better readability.

    :param df: The DataFrame to convert.
    :return: Formatted string representation of the DataFrame.
    """
    if df.empty:
        return "📉 No data available for this section.\n\n"
    else:
        return f"```{df.to_string(index=False)}```\n\n"


def analyse_motion_patterns():
    """
    Analyzes motion patterns from old and new motion models, formats the results into a readable message,
    and sends the information to the VIZ component.
    """
    try:
        # Load old and new models
        base_logger.info("🔄 Loading old and new motion models from MinIO...")
        old_model = load_model_from_minio("motion", 2)
        new_model = load_model_from_minio("motion", 1)
        base_logger.info("✅ Models loaded successfully.\n")
    except Exception as e:
        base_logger.error(f"❌ Failed to load models from MinIO: {e}")
        return

    # Initialize the message with a header
    message = (
        f"📊 **📈 Motion Patterns Analysis Report 📉📊**\n\n"
        f"📅 **Report Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
    )

    # Function to perform analysis on a given model
    def analyze_model(model, model_name):
        base_logger.info(f"🔍 Performing analyses on the {model_name} model...")
        model_message = f"### 🕰️ **{model_name} Motion Model** 🕰️\n\n"

        # 1. Summary of Sleep Time and Time Outside
        sleep_summary = summary_of_sleep_time_and_time_outside(model)
        model_message += f"#### 🛌 Sleep Time and 🌳 Time Outside Summary\n\n"
        model_message += dataframe_to_text(sleep_summary)

        # 2. Daily Visits Counts
        visits_states = ['bathroom', 'kitchen', 'livingroombedarea', 'livingroomdoor']
        for state in visits_states:
            daily_visits = count_daily_visits(model, transition_state=state)
            model_message += f"#### 🚽 **Daily Visits to {state.capitalize()}**\n\n"
            model_message += dataframe_to_text(daily_visits)

        # 3. Wake-Up Times
        wake_up_times = detect_wake_up_times(model)
        model_message += f"#### 🌅 **Wake-Up Times**\n\n"
        model_message += dataframe_to_text(wake_up_times)

        # 4. Went-To-Sleep Times
        went_to_sleep_times = detect_went_to_sleep_times(model)
        model_message += f"#### 🌙 **Went-To-Sleep Times**\n\n"
        model_message += dataframe_to_text(went_to_sleep_times)

        # 5. Transition Counts
        transition_counts = model.groupby(['from', 'to']).size().reset_index(name='count')
        model_message += f"#### 🔄 **Transition Counts Between Areas**\n\n"
        model_message += dataframe_to_text(transition_counts)

        # 6. Transition Matrix
        transition_matrix = model.groupby(['from', 'to']).size().unstack(fill_value=0)
        model_message += f"#### 📊 **Transition Matrix**\n\n"
        model_message += f"```{transition_matrix.to_string()}```\n\n"

        # Append the model analysis to the main message
        return model_message

    # Analyze old model
    old_model_message = analyze_model(old_model, "Old")
    message += old_model_message

    # Analyze new model
    new_model_message = analyze_model(new_model, "New")
    message += new_model_message

    # Send the compiled message
    try:
        send_info("🚶 Motion Patterns Analysis Report 🚶", message, level=1)
        base_logger.info("📤 Motion Patterns Analysis Report sent successfully.")
        return message
    except Exception as e:
        base_logger.error(f"❌ Failed to send Motion Patterns Analysis Report: {e}")
        return message 



