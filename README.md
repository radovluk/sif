# Digital Twin App


## Overview

Digital Twin App is a comprehensive home monitoring system designed to enhance patient safety and security within a home environment. It leverages a combination of sensor data, machine learning models, and real-time monitoring to detect emergencies, burglaries, and analyze motion patterns. The system is modular, scalable, and built with a focus on reliability and ease of deployment.

## Architecture

### Design Choices

1. **Microservices Architecture**: The project is divided into distinct modules (`actuation`, `modeling`, `monitoring`, `viz-component`, `homecare-hub-main`)

2. **Containerization with Docker**: Each module has its own `Dockerfile`, enabling isolated environments and simplifying the deployment process.

3. **Kubernetes for Orchestration**: Kubernetes manifests (`k8s/` directories) are provided for orchestrating containers, ensuring high availability and scalability.

4. **FastAPI for APIs**: Utilizes FastAPI to create asynchronous, high-performance APIs for handling various functionalities like emergency detection and model training.

5. **MinIO for Object Storage**: Chosen for its compatibility with S3 APIs, MinIO is used to store machine learning models and other artifacts.

6. **InfluxDB for Time-Series Data**: Selected for efficient storage and querying of sensor data, enabling real-time analytics and monitoring.

7. **Vue.js and Nuxt.js for Frontend**: Provides a responsive and dynamic user interface for interacting with the HomeCare Hub system.

8. **Logging and Monitoring**: Implements logging mechanisms (`log.log`, `my_app.log`) to facilitate debugging and system monitoring.



### Common Base Folder

`actuation`, `modeling`, `monitoring` have a common base folder. Every base folder contains the following utility modules:

- `event.py`: Defines event classes used across different modules. (Given)
- `gateway.py`: Manages the API gateway interactions. (Given)
- `trigger.py`: Contains the functionality to trigger functions and events. (Given)
- `homecare_hub_utils.py`: Contains utility functions for communication with the frontend.
    - **send_info**: Sends an informational item to the `/api/info` endpoint of the VIZ component.
    - **send_todo**: Sends a ToDo item to the `/api/todo` endpoint of the VIZ component.
- `influx_utils.py`: Handles interactions with InfluxDB for fetching sensor data.
    - **fetch_data**: Fetches data from InfluxDB for a specified bucket, measurement, and field within a time range.
    - **fetch_data_from_buckets**: Fetches data from multiple buckets, measurements, and fields within a time interval.
    - **fetch_all_data**: Aggregates sensor and battery data from different buckets.
    - **fetch_battery_info**: Fetches only battery information within a time interval.
    - **fetch_all_sensor_data**: Fetches all sensor data (PIR and Magnetic Switch) within a specified time range.
    - **delete_last_x_hours**: Deletes data from a specified InfluxDB bucket within the last `x_hours`.
- `minio_utils.py`: Manages interactions with MinIO for model storage and retrieval.
    - **initialize_minio_client**: Initializes and returns a MinIO client.
    - **save_model_to_minio**: Saves a model (pandas DataFrame) to MinIO, keeping the last two versions and updating a pointer file.
    - **load_model_from_minio**: Loads the latest or second-to-last model statistics DataFrame from MinIO by reading a pointer file.
- `__init__.py`: Initializes the Python package.


## Configuration

### Environment Variables

The system relies on several environment variables for configuration. These can be set in a `config.py` file or directly in the deployment environment. (For each one of `actuation`, `modeling`, `monitoring`)

#### Common Variables (Found in `config.py`)

- **CURRENT_IP**: The IP address of the raspeberry-pi. 

  ```python
  CURRENT_IP = "192.168.81.143"
  ```

- **InfluxDB Configuration**
  - `INFLUX_ORG`: InfluxDB organization name. Default: `"wise2024"`.
  - `INFLUX_TOKEN`: InfluxDB host URL or token. Default: `"{CURRENT_IP}:8086"`.
  - `INFLUX_USER`: InfluxDB username. Default: `"admin"`.
  - `INFLUX_PASS`: InfluxDB password. Default: `"secure_influx_iot_user"`.

- **MinIO Configuration**
  - `MINIO_ENDPOINT`: MinIO server URL. Default: `"{CURRENT_IP}:9090"`.
  - `MINIO_ACCESS_KEY`: Access key for MinIO. Default: `"9JyddmA0YyaIxd6Kl5pO"`.
  - `MINIO_SECRET_KEY`: Secret key for MinIO. Default: `"N8iyTd2nJGgBKUVvnrdDRlFvyZGOM5macCTAIADJ"`.
  - `MINIO_BUCKET`: Bucket name for storing models. Default: `"models"`.
  - `MINIO_OBJECT_NAME_PREFIX`: Prefix for model objects. Default: `"model"`.

- **Visualization Component**
  - `VIZ_COMPONENT_URL`: URL for the visualization component. Default: `"http://{CURRENT_IP}:9000"`.

- **Sensor Configuration**
  - `SENSOR_DATA`: Dictionary defining sensors and their corresponding buckets.
  - `BUCKET_DICT`: Mapping of sensor buckets to human-readable names.
  - `BUCKETS`, `PIR_BUCKETS`, `MAGNETIC_SWITCH_BUCKETS`, `BATTERY_BUCKETS`: Lists categorizing different sensor buckets.


## 1. Actuation

**Purpose**: Manages actuation events, including sending notifications for emergencies and burglaries.

- **`main.py`**: Defines API endpoints for creating and handling emergency and burglary notifications. It includes functions such as:

    - `create_emergency_notification_function`: Sends the information about the emergency with the custom emergency message.
    - `create_burglary_notification_function`: Sends the information about the burglary event with a custom message.

### Custom Messages

#### Burglary Notification

The `create_burglary_message` function generates a formatted message based on burglary detection results. Here are the possible messages:

- **Burglary Detected**:
    ```
    🚔 **Burglary Alert!** 🚔
    Potential burglary detected with the following details:

    🔹 **From:** [from_room] ➡️ **To:** [to_room]
    🔸 **Leave Time:** [leave_time]
    🔸 **Enter Time:** [enter_time]

    ⚠️ Please check the premises immediately. ⚠️
    ```

- **No Anomalies Detected**:
    ```
    ✅ **All Clear!** No unusual activities detected.
    Everything is normal. Have a great day! 😊
    ```

#### Emergency Notification

The `detect_emergency` function generates a formatted message based on emergency detection results. Here are the possible messages:

- **Emergency Detected**:
    ```
    🚨 Emergency Alert! 🚨
    Room: [room].
    Patient has spent [duration] here.
    Expected duration (mean): [mean],
    Standard deviation (std): [std],
    Duration is outside the expected value with no variability allowed.
    ```

- **No Emergency Detected**:
    ```
    ✅ All is well! ✅
    Patient is currently in [room] for [duration].
    No emergency detected.
    Expected duration matches the recorded duration: [mean].
    ```

- **Duration Outside Allowed Range**:
    ```
    🚨 Emergency Alert! 🚨
    Room: [room],
    Patient has spent [duration] here.
    Expected duration (mean): [mean],
    Standard deviation (std): [std],
    Threshold used: [threshold],
    Allowed duration range: [lower_bound] - [upper_bound],
    Duration is outside the allowed range!
    ```

- **Normal Status**:
    ```
    ✅ All is well! ✅
    Patient is currently in [room] for [duration].
    No emergency detected.
    Expected duration (mean): [mean],
    Standard deviation (std): [std],
    Allowed duration range: [lower_bound] - [upper_bound].
    ```

- **Door Open Event**:
    ```
    🚪 Living room door opening event detected. Not considered for emergency detection.
    ```

- **Configuration File**: `config.py` manages configuration settings, including IP addresses, intervals for model training, and sensor configurations. This file centralizes the configuration parameters required for the actuation module to function correctly.


## 2. Modeling

**Purpose**: Responsible for training and managing machine learning models for occupancy, motion, and burglary detection.

- **`main.py`**: Defines API endpoints for training occupancy, motion, and burglary models.
- **`occupancy_model.py`**: Contains functions for preparing data and training occupancy models.
- **`motion_model.py`**: Handles data preprocessing and training for motion analysis.
- **`burglary_model.py`**: Implements the burglary detection logic using Isolation Forests.

### Occupancy Model

**Purpose**: The `occupancy_model.py` script is designed to prepare sensor data and train models to predict room occupancy based on sensor readings.

- **`map_sensor_to_room`**: Maps sensor names to corresponding room or event labels.
- **`prepare_data_for_occupancy_model`**: Prepares sensor data for model training by converting timestamps, sorting data, and encoding sensor labels.
- **`calculate_times_in_each_room`**: Calculates the duration of time spent in each room or event based on sensor data. That Is done by following:

    1. Identifies room-change points and assigns group IDs.
    2. Calculates start and end times for each group.
    4. Computes the duration and duration in seconds for each group.
    5. Excludes all door-opening events from the results. (Door opening also triggers room change)

- **`train_occupancy_model`**: Computes the mean and standard deviation of time spent in each room to train the occupancy model.

### Motion Model

**Purpose**: The `motion_model.py` script is designed to preprocess sensor data and analyze motion patterns to train models for motion analysis.

- **`data_preprocessing_motion_analysis`**: Preprocesses the sensor data by parsing timestamps, identifying value changes, and extracting temporal features.
    - Ensures the 'timestamp' column is in datetime format.
    - Sorts the DataFrame by timestamp to ensure chronological order.
    - Creates a column to identify when 'value' changes and assigns a group ID that increments when 'value' changes.
    - Groups by 'group_id' and aggregates relevant information.
    - Calculates duration in seconds between enter and leave times.
    - Extracts temporal features from the enter_time.
- **`create_transition_dataframe`**: Creates a Transition DataFrame capturing movements between rooms based on consecutive different 'value' entries.
    - Handles special transitions like 'went out' or 'went to sleep' based on time gaps and time of day.
    - Initializes a list to store transitions and iterates through the DataFrame to capture movements.
    - Creates the Transition DataFrame and handles cases where 'from' or 'to' might be missing.
- **`train_motion_model`**: Trains the motion model by analyzing sensor data to identify movement patterns between different states.
    - Fetches sensor data for a specified time window.
    - Prepares the fetched data for occupancy modeling.
    - Processes the prepared data to analyze motion events and extract relevant features.
    - Creates a transition DataFrame to capture movements between different motion states.
    - Returns the transition DataFrame. Future enhancements should include training advanced models and storing them in MinIO.

### Burglary Model

**Purpose**: The `burglary_model.py` script is designed to detect potential burglary activities using Isolation Forests.

- **`class BurglaryDetector`**: Implements the burglary detection logic.
    - **`__init__`**: Initializes the BurglaryDetector with specified Isolation Forest parameters.
    - **`_feature_engineering`**: Performs feature engineering on the DataFrame.
    - **`train`**: Trains the Isolation Forest model on the provided DataFrame.
    - **`detect`**: Detects anomalies in the new motion data.
    - **`visualize_anomalies`**: Visualizes anomalies using a scatter plot.
    - **`save_model`**: Saves the trained model to MinIO.
    - **`load_model`**: Loads the trained model from MinIO.
- **`train_burglary_model`**: Trains the BurglaryDetector model using motion data and saves the trained model to MinIO.



## 3. Monitoring

**Purpose**: This component focuses on detecting anomalies and monitoring activities for emergency detection, burglary detection, and motion analysis. It implements scheduled and event-driven workflows for analyzing patterns and triggering necessary alerts.

### Configuration of Trigger Times

The system uses environment variables to configure the intervals and wait times for various triggers. These settings ensure that the models are retrained and the data is analyzed at regular intervals.

- **TRAIN_OCCUPANCY_MODEL_INTERVAL**: `"12h"` - The occupancy model will be retrained every 12 hours.
- **TRAIN_OCCUPANCY_MODEL_WAIT_TIME**: `"30s"` - Wait 30 seconds before starting the first retraining.

- **TRAIN_MOTION_MODEL_INTERVAL**: `"12h"` - The motion model will be retrained every 12 hours.
- **TRAIN_MOTION_MODEL_WAIT_TIME**: `"15s"` - Wait 15 seconds before starting the first retraining.

- **ANALYSE_MOTION_INTERVAL**: `"24h"` - Motion analysis will be performed every 24 hours.
- **ANALYSE_MOTION_WAIT_TIME**: `"20s"` - Wait 20 seconds before starting the first motion analysis.

- **TRAIN_BURGLARY_MODEL_INTERVAL**: `"12h"` - The burglary model will be retrained every 12 hours.
- **TRAIN_BURGLARY_MODEL_WAIT_TIME**: `"30s"` - Wait 30 seconds before starting the first retraining.

- **CHECK_BURGLARY_INTERVAL**: `"1h"` - Burglary detection will be checked every hour.
- **CHECK_BURGLARY_WAIT_TIME**: `"40s"` - Wait 40 seconds before starting the first burglary check.

- **CHECK_EMERGENCY_INTERVAL**: `"30m"` - Emergency detection will be checked every 30 minutes.
- **CHECK_EMERGENCY_WAIT_TIME**: `"50s"` - Wait 50 seconds before starting the first emergency check.

- **TRESHOLD_FOR_EMERGENCY_DETECTION**: `3` - Number of standard deviations from the mean to trigger an emergency.

- **START_HOURS_FOR_EMERGENCY_DETECTION**: `24 * 7 * 4` - Start of the interval for fetching data used for emergency detection.
- **INTERVAL_HOURS_FOR_EMERGENCY_DETECTION**: `24 * 7 * 4` - Duration of the interval for fetching data used for emergency detection.

- **TRAINING_DATA_WINDOW_HOURS**: `24 * 7 * 2` - How old data to use for retraining the occupancy model.

**Important Sections**:
- **Periodic Triggers**: Configures triggers that periodically invoke detection workflows.


## Features
1. **Emergency Detection**
   - Monitors data to detect emergency situations using specified thresholds.
   - Asynchronous function to handle incoming data and trigger appropriate events.

2. **Burglary Detection**
   - Uses Isolation Forest for anomaly detection in motion data.
   - Triggers alerts if suspicious patterns are detected.

3. **Motion Analysis**
   - Analyzes daily patterns, sleep, and activity durations.
   - Generates visualizations such as heatmaps and transaction graphs for insights.



### Main Functions
- **`check_emergency_detection_function`**: Checks for emergencies based on incoming data.
- **`check_burglary_detection_function`**: Detects anomalies indicating potential burglaries.
- **`motion_analysis_function`**: Analyzes motion patterns and generates reports.

### Event Management
- Utilizes `PeriodicTrigger` and `OneShotTrigger` for scheduling and handling events.
- Event classes include:
  - `TrainOccupancyModelEvent`
  - `CheckEmergencyEvent`
  - `EmergencyEvent`
  - `TrainMotionModelEvent`
  - `AnalyzeMotionEvent`
  - `TrainBurglaryModelEvent`
  - `CheckBurglaryEvent`
  - `BurglaryEvent`


## Data Visualization
### Heatmaps
Visualizes sensor transitions using `seaborn`.
- Daily summaries.
- Segmented by time of day (Morning, Afternoon, Evening, Night).

### Transaction Graphs
Creates bidirectional graphs using `networkx` to show movement patterns.


```
MIT License

Copyright (c) 2024 CAPS-IoT

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

*For further assistance or inquiries, please contact the project maintainer.*
