import logging
import pandas as pd

base_logger = logging.getLogger(__name__)

def train_motion_model():
    """
    Train motion model.
    1. Get Occupancy and Door Events
    2. Store New Motion Model
        • Description: This model captures the typical behavior for a period.
        • Storage: Minio
        • Metadata: timestamp, ID specifying calendar week
        • Training: per week
        • MotionPatternsModel: Going for Room A to Room B at 8:20
        • Neural Networks, Holt-Winters, Markov-Chain, Temporal Point Processes
            • Description: Computes the MotionModel and stores it in minio
            • Input: Timeseries RoomOccupancy and DoorActions of that period.
            • Output: MotionModel
            • Subscription: TrainMotionModelEvent
    """
    base_logger.info(f"train_motion_model() called. Training motion model. Not implemented yet.")

def analyse_motion_patterns():
    """
    Analyse motion patterns.
    1. Get Motion Models of last two periods
    2. Store Motion Analysis Report
    3. Publish Analysis Report as Info List Item
        • Description: Compares the last two motion models and generates a report.
        • Subscription: AnalyzeMotionEvent
        • Input: MotionModel of the last two periods
        • Output: Report to be stored in minio and send to the info list of the visualization
    """
    base_logger.info(f"analyse_motion_patterns() called. Analysing motion model. Not implemented yet.")