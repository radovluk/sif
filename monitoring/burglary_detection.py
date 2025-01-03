from base.minio_utils import load_model_from_minio, save_model_to_minio
from motion_model import train_motion_model
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import pickle
import base64
from io import BytesIO, StringIO
import json
from typing import Optional
import logging

base_logger = logging.getLogger(__name__)


class BurglaryDetector:
    def __init__(self, contamination='auto', random_state=42, model_type: str = 'burglary'):
        """
        Initializes the BurglaryDetector with specified Isolation Forest parameters.

        Parameters:
        - contamination: float, 'auto' or float, the proportion of anomalies in the data set.
        - random_state: int, random seed for reproducibility.
        - model_type: str, identifier for the model type (used in MinIO storage).
        """
        self.contamination = contamination
        self.random_state = random_state
        self.model = None
        self.preprocessor = None
        self.feature_columns = None
        self.model_type = model_type  # e.g., 'burglary'

    def _feature_engineering(self, df: pd.DataFrame):
        """
        Performs feature engineering on the DataFrame.

        Parameters:
        - df: pandas DataFrame with columns ['from', 'to', 'leave_time', 'enter_time'].

        Returns:
        - df_features: pandas DataFrame with engineered features for modeling.
        - df_original: pandas DataFrame with original and some engineered features for reporting.
        """
        # Retain original timestamps and additional features for reporting
        df_original = df[['from', 'to', 'leave_time', 'enter_time']].copy()

        # Encode categorical variables
        categorical_features = ['from', 'to']
        self.preprocessor = ColumnTransformer(
            transformers=[
                ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
            ],
            remainder='passthrough'  # Keep other columns
        )

        # Convert datetime columns
        df['leave_time'] = pd.to_datetime(df['leave_time'])
        df['enter_time'] = pd.to_datetime(df['enter_time'])

        # Feature engineering: duration and temporal features
        df['duration'] = (df['enter_time'] - df['leave_time']).dt.total_seconds()

        # Extract temporal features from leave_time
        df['leave_hour'] = df['leave_time'].dt.hour
        df['leave_minute'] = df['leave_time'].dt.minute
        df['leave_second'] = df['leave_time'].dt.second

        # Extract temporal features from enter_time
        df['enter_hour'] = df['enter_time'].dt.hour
        df['enter_minute'] = df['enter_time'].dt.minute
        df['enter_second'] = df['enter_time'].dt.second

        # Retain 'duration' and 'leave_hour' in df_original for visualization
        df_original['duration'] = df['duration']
        df_original['leave_hour'] = df['leave_hour']

        # Drop original datetime columns
        df.drop(['leave_time', 'enter_time'], axis=1, inplace=True)

        # The DataFrame to be used for modeling
        df_features = df.copy()

        return df_features, df_original

    def train(self, df: pd.DataFrame):
        """
        Trains the Isolation Forest model on the provided DataFrame.

        Parameters:
        - df: pandas DataFrame with columns ['from', 'to', 'leave_time', 'enter_time'].
        """
        # Feature engineering
        df_features, _ = self._feature_engineering(df.copy())

        # Separate features and prepare the pipeline
        X = df_features.copy()

        # Initialize Isolation Forest within a Pipeline
        self.model = Pipeline(steps=[
            ('preprocessor', self.preprocessor),
            ('classifier', IsolationForest(
                n_estimators=100,
                contamination=self.contamination,
                random_state=self.random_state
            ))
        ])

        # Fit the model
        self.model.fit(X)

        # Store feature columns after preprocessing for reference
        self.feature_columns = self.model.named_steps['preprocessor'].get_feature_names_out()

        print("Model training completed.")

    def detect(self, new_df: pd.DataFrame):
        """
        Detects anomalies in the new motion data.

        Parameters:
        - new_df: pandas DataFrame with columns ['from', 'to', 'leave_time', 'enter_time'] representing the last hour's motions.

        Returns:
        - result_df: pandas DataFrame with original and some engineered features along with 'anomaly' and 'anomaly_label' columns.
        - is_burglary: Boolean indicating whether an anomaly (potential burglary) was detected.
        """
        if self.model is None:
            raise Exception("The model has not been trained yet. Call the train() method first.")

        # Feature engineering
        df_features, df_original = self._feature_engineering(new_df.copy())

        # Predict anomalies
        predictions = self.model.predict(df_features)

        # Append predictions to the original DataFrame
        df_original['anomaly'] = predictions

        # Map predictions to more interpretable labels
        df_original['anomaly_label'] = df_original['anomaly'].map({1: 'Normal', -1: 'Anomaly'})

        # Identify if any anomaly exists in the last hour
        is_burglary = df_original['anomaly'].isin([-1]).any()

        base_logger.info(f"Anomaly detected: {'Yes' if is_burglary else 'No'}")
        return df_original, is_burglary

    def visualize_anomalies(self, df_processed: pd.DataFrame):
        """
        Visualizes anomalies using a scatter plot.

        Parameters:
        - df_processed: pandas DataFrame after prediction with 'anomaly_label' column.
        """
        # Check if required columns are present
        if not {'leave_hour', 'duration', 'anomaly_label'}.issubset(df_processed.columns):
            raise ValueError("The DataFrame must contain 'leave_hour', 'duration', and 'anomaly_label' columns for visualization.")

        plt.figure(figsize=(10, 6))
        sns.scatterplot(data=df_processed, x='leave_hour', y='duration', hue='anomaly_label', palette=['blue', 'red'])
        plt.title('Anomaly Detection based on Leave Hour and Duration')
        plt.xlabel('Leave Hour')
        plt.ylabel('Duration (seconds)')
        plt.legend(title='Status')
        plt.show()

    def save_model(self):
        """
        Saves the trained model to MinIO using the provided save_model_to_minio function.
        The model is serialized using pickle and encoded in base64 to be stored as a JSON-compatible string.
        """
        if self.model is None:
            raise Exception("No model to save. Train the model before saving.")

        # Serialize the model using pickle to bytes
        serialized_model = pickle.dumps(self.model)

        # Encode the serialized model to a base64 string
        encoded_model = base64.b64encode(serialized_model).decode('utf-8')

        # Create a DataFrame to store the encoded model
        model_df = pd.DataFrame({
            'model_type': [self.model_type],
            'model_data': [encoded_model]
        })

        # Save the DataFrame to MinIO
        save_model_to_minio(model_df, self.model_type)

        base_logger.info("Model saved to MinIO successfully.")

    def load_model(self, version: int = 1):
        """
        Loads the trained model from MinIO using the provided load_model_from_minio function.
        The model is deserialized from a base64-encoded string.

        Parameters:
        - version: An integer specifying which version to load (1 for latest, 2 for second-to-last).
                   Defaults to 1.
        """
        # Load the DataFrame containing the encoded model from MinIO
        model_df = load_model_from_minio(self.model_type, version=version)

        if model_df is None or model_df.empty:
            raise Exception(f"Failed to load model version {version} from MinIO.")

        # Extract the encoded model string
        encoded_model = model_df['model_data'].iloc[0]

        # Decode the base64 string to bytes
        serialized_model = base64.b64decode(encoded_model.encode('utf-8'))

        # Deserialize the model using pickle
        self.model = pickle.loads(serialized_model)

        print(f"Model version {version} loaded from MinIO successfully.")

def create_burglary_message(detection_df: pd.DataFrame, is_burglary: bool):
    """
    Generates a formatted message based on burglary detection results.
    
    Parameters:
    - detection_df (pd.DataFrame): DataFrame containing detection results with columns:
        ['from', 'to', 'leave_time', 'enter_time', 'anomaly_label']
    - is_burglary (bool): Flag indicating if any anomalies were detected.
    
    Returns:
    - Optional[str]: Formatted message string or None if no message is generated.
    """
    if is_burglary:
        # Extract anomalies
        anomalies = detection_df[detection_df['anomaly_label'] == 'Anomaly']
        if anomalies.empty:
            base_logger.warning("is_burglary is True but no anomalies found in the DataFrame.")
            return None
        
        # Initialize message components
        message_header = "🚔 **Burglary Alert!** 🚔\n"
        message_body = "Potential burglary detected with the following details:\n\n"
        
        # Iterate through each anomaly to build the message
        for idx, row in anomalies.iterrows():
            from_room = row['from']
            to_room = row['to']
            leave_time = row['leave_time']
            enter_time = row['enter_time']
            
            # Format times
            leave_time_str = pd.to_datetime(leave_time).strftime('%Y-%m-%d %H:%M:%S')
            enter_time_str = pd.to_datetime(enter_time).strftime('%Y-%m-%d %H:%M:%S')
            
            # Construct transition description
            transition_desc = (
                f"🔹 **From:** {from_room} ➡️ **To:** {to_room}\n"
                f"🔸 **Leave Time:** {leave_time_str}\n"
                f"🔸 **Enter Time:** {enter_time_str}\n\n"
            )
            message_body += transition_desc
        
        # Add concluding statement
        message_footer = "⚠️ Please check the premises immediately. ⚠️"
        
        # Combine all parts
        full_message = message_header + message_body + message_footer
        base_logger.info("Burglary alert message created successfully.")
        return full_message
    else:
        # No anomalies detected
        message = "✅ **All Clear!** No unusual activities detected.\n"
        message += "Everything is normal. Have a great day! 😊"
        base_logger.info("No anomalies detected. Normal status message created.")
        return message

def detect_burglary(start_hours=24, interval_hours=24, time_threshold_seconds=1800):
    """
    Detects potential burglaries based on motion data and generates an appropriate message.
    
    This function performs the following steps:
    1. Initializes the BurglaryDetector with specified parameters.
    2. Loads the latest trained model from MinIO.
    3. Trains the motion model using the provided parameters.
    4. Detects anomalies in the trained motion model.
    5. Generates a formatted message based on the detection results.
    
    Parameters:
    - start_hours (int): Starting hours for motion data analysis.
    - interval_hours (int): Number of hours over which to aggregate motion data (e.g., 24 for daily).
    - time_threshold_seconds (int): Threshold in seconds to filter motion durations (e.g., 1800 for 30 minutes).
    
    Returns:
    - Tuple[Optional[bool], Optional[str]]: A tuple containing:
        - is_burglary (bool): Indicates whether any anomalies (potential burglaries) were detected.
        - message (str): A formatted message detailing the detection results.
    """
    detector = BurglaryDetector(contamination=0.01, model_type='burglary')
    detector.load_model(version=1)
    motion_model = train_motion_model(start_hours=start_hours, interval_hours=interval_hours, time_threshold_seconds=time_threshold_seconds)
    detection = detector.detect(motion_model)
    message = create_burglary_message(detection[0], detection[1])
    return detection[1], message