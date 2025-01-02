import logging
import pandas as pd
from sklearn.preprocessing import LabelEncoder

base_logger = logging.getLogger(__name__)


def train_burglary_model():
    """
    Train burglary model.

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
    base_logger.info(f"Function train_burglary_model() called. Not yet implemented")
    pass
