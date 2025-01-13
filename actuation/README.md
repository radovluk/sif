# Actuation Component

## Overview

The **Actuation Component** is a critical module within the Digital Twin App ecosystem, responsible for managing actuation events such as sending notifications for emergencies and burglaries. 

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
  - [Directory Structure](#directory-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [API Endpoints](#api-endpoints)
- [Deployment](#deployment)
  - [Docker](#docker)
  - [Kubernetes](#kubernetes)
- [Utilities](#utilities)
  - [HomeCare Hub Utilities](#homecare-hub-utilities)
  - [InfluxDB Utilities](#influxdb-utilities)
  - [MinIO Utilities](#minio-utilities)
- [Logging](#logging)
- [Contributing](#contributing)
- [License](#license)

## Features

1. **Emergency Notification**
   - Detects and sends notifications for emergency situations based on sensor data.
   
2. **Burglary Notification**
   - Identifies potential burglary events and triggers appropriate alerts.
   
3. **Scalable API**
   - Built with FastAPI to handle high-throughput event processing asynchronously.
   
4. **Containerization & Orchestration**
   - Dockerized for consistent environments.
   - Kubernetes manifests provided for scalable deployments.
   
5. **Integration with InfluxDB & MinIO**
   - Fetches sensor data from InfluxDB.
   - Stores and retrieves models using MinIO object storage.

## Architecture

### Directory Structure

```
actuation/
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
├── __pycache__
│   └── config.cpython-312.pyc
└── requirements.txt
```

- **base/**: Contains utility modules and common functionalities.
- **config.py**: Configuration settings and environment variables.
- **Dockerfile**: Instructions to build the Docker image.
- **k8s/**: Kubernetes manifests for deployment, service, and config maps.
- **main.py**: Entry point of the Actuation Component application.
- **requirements.txt**: Python dependencies.

## Installation

### Prerequisites

- Python 3.12+
- Docker
- Kubernetes cluster (for deployment)
- Access to InfluxDB and MinIO instances

### Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/your-repo/actuation.git
   cd actuation
   ```

2. **Create a Virtual Environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**

   Update the `config.py` file with the necessary configurations (see [Configuration](#configuration) section).

## Configuration

The Actuation Component relies on several environment variables defined in `config.py`. These variables can also be set via environment variables in the deployment environment.

### `config.py`

```python
# In config.py

CURRENT_IP = "192.168.81.143"

# InfluxDB Configuration
INFLUX_ORG = "wise2024"
INFLUX_TOKEN = f"http://{CURRENT_IP}:8086"
INFLUX_USER = "admin"
INFLUX_PASS = "secure_influx_iot_user"

# MinIO Configuration
MINIO_ENDPOINT = f"{CURRENT_IP}:9090"
MINIO_ACCESS_KEY = "9JyddmA0YyaIxd6Kl5pO"
MINIO_SECRET_KEY = "N8iyTd2nJGgBKUVvnrdDRlFvyZGOM5macCTAIADJ"
MINIO_BUCKET = "models"
MINIO_OBJECT_NAME_PREFIX = "model"

# Visualization Component
VIZ_COMPONENT_URL = f"http://{CURRENT_IP}:9000"

# Sensor Configuration
SENSOR_DATA = {...}  # Define your sensor data mappings
BUCKET_DICT = {...}   # Define bucket to sensor name mappings
BUCKETS = [...]
PIR_BUCKETS = [...]
MAGNETIC_SWITCH_BUCKETS = [...]
BATTERY_BUCKETS = [...]
```

### Environment Variables

- **CURRENT_IP**: IP address of the Raspberry Pi or host machine.
- **InfluxDB Settings**: Credentials and connection details for InfluxDB.
- **MinIO Settings**: Credentials and connection details for MinIO object storage.
- **VIZ_COMPONENT_URL**: URL for the visualization component.
- **Sensor Configurations**: Mappings and lists for sensor data buckets.

## Usage


### API Endpoints

#### 1. Create Emergency Notification

- **Endpoint**: `/create_emergency_notification_function`
- **Method**: `POST`
- **Description**: Handles incoming emergency notifications and sends alerts.
- **Request Body**: JSON containing emergency details.

**Example Request**

```bash
curl -X POST "http://localhost:8000/create_emergency_notification_function" \
     -H "Content-Type: application/json" \
     -d '{"room": "Living Room", "duration": 120}'
```

**Example Response**

```json
{
  "status": "success"
}
```

#### 2. Create Burglary Notification

- **Endpoint**: `/create_burglary_notification_function`
- **Method**: `POST`
- **Description**: Handles incoming burglary notifications and sends alerts.
- **Request Body**: JSON containing burglary details.

**Example Request**

```bash
curl -X POST "http://localhost:8000/create_burglary_notification_function" \
     -H "Content-Type: application/json" \
     -d '{"from_room": "Kitchen", "to_room": "Bedroom", "leave_time": "10:00", "enter_time": "10:05"}'
```

**Example Response**

```json
{
  "status": "success"
}
```

## Deployment

### Docker

1. **Build the Docker Image**

   ```bash
   docker build -t actuation-component:latest .
   ```

2. **Run the Docker Container**

   ```bash
   docker run -d -p 8000:8000 --env-file .env actuation-component:latest
   ```

### Kubernetes

1. **Apply ConfigMap**

   ```bash
   kubectl apply -f k8s/configmap.yml
   ```

2. **Deploy the Application**

   ```bash
   kubectl apply -f k8s/deployment.yml
   ```

3. **Expose the Service**

   ```bash
   kubectl apply -f k8s/service.yml
   ```

   The Actuation Component will be accessible within the Kubernetes cluster or externally based on the service configuration.

## Utilities

### HomeCare Hub Utilities

Located in `base/homecare_hub_utils.py`, this module provides functions to communicate with the visualization component.

- **`send_info(summary: str, detail: str, level: int) -> None`**
  - Sends informational messages to the `/api/info` endpoint.
  
- **`send_todo(title: str, message: str, level: int) -> None`**
  - Sends ToDo items to the `/api/todo` endpoint.

### InfluxDB Utilities

Located in `base/influx_utils.py`, this module handles interactions with InfluxDB for fetching sensor data.

- **`fetch_data(...)`**
  - Fetches data from a specific bucket, measurement, and field.
  
- **`fetch_data_from_buckets(...)`**
  - Fetches data from multiple buckets.
  
- **`fetch_all_data(...)`**
  - Aggregates all sensor and battery data.
  
- **Additional Functions**
  - `fetch_battery_info`, `fetch_all_sensor_data`, etc.

### MinIO Utilities

Located in `base/minio_utils.py`, this module manages interactions with MinIO for storing and retrieving models.

- **`initialize_minio_client() -> Optional[Minio]`**
  - Initializes the MinIO client.
  
- **`save_model_to_minio(room_stats: pd.DataFrame, model_type: str) -> None`**
  - Saves model data to MinIO, maintaining versioning.
  
- **`load_model_from_minio(model_type: str, version: int = 1) -> Optional[pd.DataFrame]`**
  - Loads model data from MinIO based on version.

## Logging

Logging is implemented using Python's `logging` module. Logs provide insights into the application's behavior and are essential for debugging and monitoring.

- **Log Files**
  - Logs are typically output to the console. Configure log handlers in your deployment environment as needed.

- **Log Levels**
  - `INFO`: General operational messages.
  - `ERROR`: Issues that prevent some functionality from working.
  - `WARNING`: Indications of potential problems.


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
