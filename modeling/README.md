# Modeling Component

## Overview

The **Modeling Component** of the Digital Twin App is responsible for training machine learning models for occupancy, motion, and burglary detection. These models are integral to monitoring patient activity, analyzing motion patterns, and ensuring home security. The component uses FastAPI to handle API requests for model training and integrates with MinIO for model storage and InfluxDB for sensor data retrieval.

## Features

1. **Occupancy Model Training**
   - Analyzes sensor data to determine patient presence in different rooms.
   - Uses statistical methods to calculate room-specific mean and standard deviation.
   - Stores trained models in MinIO for future use.

2. **Motion Model Training**
   - Detects and analyzes motion patterns using sensor transitions.
   - Handles complex scenarios like prolonged inactivity and specific time thresholds.

3. **Burglary Model Training**
   - Utilizes anomaly detection (e.g., Isolation Forest) to identify potential burglaries.
   - Processes extended periods of motion data for robust model accuracy.

4. **Asynchronous API Integration**
   - FastAPI allows efficient handling of requests for model training.
   - Separate endpoints for each model type.

5. **MinIO Integration**
   - Stores trained models with versioning.

6. **InfluxDB Integration**
   - Fetches historical sensor data for model training.

## Architecture

### Directory Structure

```
modeling/
├── base
│   ├── __init__.py
│   ├── event.py
│   ├── gateway.py
│   ├── homecare_hub_utils.py
│   ├── influx_utils.py
│   ├── minio_utils.py
│   ├── trigger.py
│   └── __pycache__
├── config.py
├── Dockerfile
├── k8s
│   ├── configmap.yml
│   ├── deployment.yml
│   └── service.yml
├── LICENSE
├── main.py
├── occupancy_model.py
├── motion_model.py
├── burglary_model.py
├── __pycache__
└── requirements.txt
```

- **base/**: Common utilities shared across components.
- **config.py**: Configuration and environment variables.
- **occupancy_model.py**: Logic for occupancy model training.
- **motion_model.py**: Logic for motion model training.
- **burglary_model.py**: Logic for burglary model training.
- **main.py**: FastAPI entry point and function deployments.

## Configuration

### Environment Variables

The component relies on several environment variables defined in `config.py`:

```python
# InfluxDB Configuration
INFLUX_ORG = "wise2024"
INFLUX_TOKEN = "<InfluxDB_Token>"
INFLUX_USER = "admin"
INFLUX_PASS = "secure_influx_iot_user"

# MinIO Configuration
MINIO_ENDPOINT = "<MinIO_Endpoint>"
MINIO_ACCESS_KEY = "<Access_Key>"
MINIO_SECRET_KEY = "<Secret_Key>"
MINIO_BUCKET = "models"

# Training Data Configuration
TRAINING_DATA_WINDOW_HOURS = 24 * 7 * 4  # 4 weeks
```

## API Endpoints

### 1. Create Occupancy Model

- **Endpoint**: `/create_occupancy_model_function`
- **Method**: `POST`
- **Event Triggered**: `TrainOccupancyModelEvent`
- **Description**: Fetches sensor data, trains the occupancy model, and saves it to MinIO.

**Example Request**:
```bash
curl -X POST "http://localhost:8000/create_occupancy_model_function" \
     -H "Content-Type: application/json" \
     -d '{}'
```

**Example Response**:
```json
{
  "status": "success"
}
```

### 2. Create Motion Model

- **Endpoint**: `/create_motion_model_function`
- **Method**: `POST`
- **Event Triggered**: `TrainMotionModelEvent`
- **Description**: Trains the motion model using recent sensor data and saves it to MinIO.

**Example Request**:
```bash
curl -X POST "http://localhost:8000/create_motion_model_function" \
     -H "Content-Type: application/json" \
     -d '{}'
```

**Example Response**:
```json
{
  "status": "success"
}
```

### 3. Create Burglary Model

- **Endpoint**: `/create_burglary_model_function`
- **Method**: `POST`
- **Event Triggered**: `TrainBurglaryModelEvent`
- **Description**: Trains the burglary model using historical motion data.

**Example Request**:
```bash
curl -X POST "http://localhost:8000/create_burglary_model_function" \
     -H "Content-Type: application/json" \
     -d '{}'
```

**Example Response**:
```json
{
  "status": "success"
}
```

## Deployment

### Docker

1. **Build the Docker Image**:
   ```bash
   docker build -t modeling-component:latest .
   ```

2. **Run the Docker Container**:
   ```bash
   docker run -d -p 8000:8000 --env-file .env modeling-component:latest
   ```

### Kubernetes

1. **Apply ConfigMap**:
   ```bash
   kubectl apply -f k8s/configmap.yml
   ```

2. **Deploy the Application**:
   ```bash
   kubectl apply -f k8s/deployment.yml
   ```

3. **Expose the Service**:
   ```bash
   kubectl apply -f k8s/service.yml
   ```

## Logging

Logging is configured with a rotating file handler to ensure logs are manageable:

```python
logging.basicConfig(
    handlers=[RotatingFileHandler("my_app.log", maxBytes=5_000_000, backupCount=5)],
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
```

Log files are stored as `my_app.log` with a maximum size of 5 MB and up to 5 backups.

## Utilities

### InfluxDB Utilities

- **`fetch_all_sensor_data`**: Fetches all sensor data for the specified time range.

### MinIO Utilities

- **`save_model_to_minio`**: Saves the trained model to MinIO with proper versioning.

### HomeCare Hub Utilities

- **`send_info`**: Sends a notification about the successful training of models.

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
