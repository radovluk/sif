# Monitoring Component

## Overview

The **Monitoring Component** is responsible for real-time detection and analysis of activities in the home environment. It trains and deploys machine learning models to identify occupancy, motion, and burglary patterns, enhancing patient safety and home security. The component integrates with InfluxDB for sensor data, MinIO for model storage, and a visualization hub for notifications and insights.

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
  - [Model Training Functions](#model-training-functions)
  - [Logging](#logging)
- [Contributing](#contributing)
- [License](#license)

## Features

1. **Model Training and Deployment**
   - Trains machine learning models for occupancy, motion, and burglary detection.
   - Automatically saves and updates models in MinIO.

2. **Event-Driven Framework**
   - Deploys asynchronous functions triggered by specific events such as `TrainOccupancyModelEvent` and `TrainMotionModelEvent`.

3. **Data Integration**
   - Fetches sensor data from InfluxDB for training models.
   - Sends notifications and insights to the visualization hub.

## Architecture

### Directory Structure

```
monitoring/
├── base
├── burglary_detection.py
├── config.py
├── Dockerfile
├── k8s
├── LICENSE
├── main.py
├── monitoring.ipynb
├── motion_analysis.py
├── motion_model.py
├── occupancy_model.py
├── patient_emergency_detection.py
├── __pycache__
├── README.md
├── requirements.txt
└── sif
```

- **base/**: Contains shared utility modules for data handling, logging, and storage.
- **burglary_detection.py**: Implements burglary detection model training.
- **motion_analysis.py**: Analyzes motion patterns and transitions.
- **motion_model.py**: Prepares and trains motion models.
- **occupancy_model.py**: Prepares and trains occupancy models.
- **main.py**: Application entry point for training and deploying models.
- **config.py**: Configuration settings and environment variables.
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
   git clone https://github.com/your-repo/monitoring.git
   cd monitoring
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

The Monitoring Component relies on several environment variables defined in `config.py`. These variables can also be set via environment variables in the deployment environment.

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
```

## Usage

### API Endpoints

#### 1. Train Occupancy Model

- **Endpoint**: `/create_occupancy_model_function`
- **Method**: `POST`
- **Description**: Trains a new occupancy model based on sensor data and saves it to MinIO.

#### 2. Train Motion Model

- **Endpoint**: `/create_motion_model_function`
- **Method**: `POST`
- **Description**: Trains a new motion model based on recent motion patterns.

#### 3. Train Burglary Model

- **Endpoint**: `/create_burglary_model_function`
- **Method**: `POST`
- **Description**: Trains a new burglary detection model and saves it to MinIO.

## Deployment

### Docker

1. **Build the Docker Image**

   ```bash
   docker build -t monitoring-component:latest .
   ```

2. **Run the Docker Container**

   ```bash
   docker run -d -p 8000:8000 --env-file .env monitoring-component:latest
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

## Utilities

### Model Training Functions

1. **Occupancy Model Training**
   - Fetches sensor data from InfluxDB.
   - Prepares data using `prepare_data_for_occupancy_model`.
   - Trains a model and saves it to MinIO.
   - Sends a notification to the visualization hub.

2. **Motion Model Training**
   - Trains a motion model with a configurable time threshold.
   - Saves the model to MinIO.
   - Sends a notification to the visualization hub.

3. **Burglary Model Training**
   - Detects anomalies in motion data using a burglary detection model.
   - Saves the trained model to MinIO.
   - Sends a notification to the visualization hub.

### Logging

Logging is implemented using Python's `logging` module with a rotating file handler. Logs are saved to `my_app.log` for debugging and monitoring purposes.

- **Log Levels**
  - `INFO`: General operational messages.
  - `ERROR`: Issues that prevent some functionality from working.
  - `WARNING`: Indications of potential problems.


## License


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
