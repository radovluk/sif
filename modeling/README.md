
# Modeling

A lightweight application for **retrieving sensor data** from InfluxDB, **training occupancy models**, and **saving them to MinIO**, all while providing simple **utility functions** for logging or sending data to a visualization component.


## Overview

**Home Care Hub** is designed to manage sensor data collected from an **InfluxDB** instance, perform **occupancy model training**, and store the resulting model artifacts in a **MinIO** object storage system. Additionally, it provides utility functions for reporting data or logging updates to a visualization component.

---

## Folder Structure

A typical layout might look like this:

```
.
├── base
│   ├── event.py
│   ├── gateway.py
│   ├── homecare_hub_utils.py
│   ├── influx_utils.py
│   ├── minio_utils.py
│   └── trigger.py
├── config.py
├── k8s
│   ├── configmap.yml
│   ├── deployment.yml
│   └── service.yml
├── main.py
├── requirements.txt
├── training.py
├── Dockerfile
├── LICENSE
└── README.md
```

- **base/**: Contains core modules (gateway, triggers, events, and utilities).  
- **config.py**: Central configuration for environment variables and constants.  
- **data/**: Holds CSV files or other data artifacts.  
- **k8s/**: Kubernetes deployment manifests.  
- **main.py**: Application entry point (e.g., gateway deployment and request handling).  
- **training.py**: Training and data-processing logic.  
- **Dockerfile**: Docker configuration for containerizing the app.  
- **requirements.txt**: Python dependencies.

---

3. **Configure** environment variables or adjust `config.py` to match your InfluxDB/MinIO setup.

4. **Run** the app (depending on how you handle your gateway logic). For example:

   ```bash
   python main.py
   ```
   
   or, if using FastAPI with `uvicorn`:

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

---

## Configuration

All environment variables and constants are defined in **`config.py`**. This includes:

- **InfluxDB** credentials (e.g., `INFLUX_TOKEN`, `INFLUX_USER`, `INFLUX_PASS`, `INFLUX_ORG`)  
- **MinIO** endpoint/credentials (e.g., `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`)  
- **Other** parameters (e.g., `FETCHED_DATA_FOR_RETRAINING_HOURS`, `BUCKET_DICT`, `VIZ_COMPONENT_URL`)

You can either set these via environment variables or modify the default values in `config.py` directly.

---

## Key Files

### **homecare_hub_utils.py**
- Located in `base/homecare_hub_utils.py`.
- Provides utility functions for logging data or sending messages to the **visualization component**. 
- Example Functions:
  - `send_info(summary, detail, level)`: Sends an informational item to the `/api/info` endpoint.
  - `send_todo(title, message, level)`: Sends a ToDo item to the `/api/todo` endpoint.

### **influx_utils.py**
- Located in `base/influx_utils.py`.
- Handles interactions with **InfluxDB**, including:
  - **Connection** setup using `InfluxDBClient`.
  - **Data fetching** (e.g., `fetch_all_data`, `fetch_battery_info`, etc.).
- Fetches sensor or battery data from multiple InfluxDB buckets.

### **minio_utils.py**
- Located in `base/minio_utils.py`.
- Manages **MinIO** operations such as:
  - **Initializing** the MinIO client.
  - **Saving** a DataFrame as a model (JSON) to the MinIO bucket.
  - **Loading** the latest model from MinIO using a pointer file (e.g., `latest.txt`).

### **config.py**
- Defines all **configuration** constants and environment variables needed for the application.
- Values such as `INFLUX_TOKEN`, `MINIO_ENDPOINT`, `VIZ_COMPONENT_URL`, etc. are declared here.
- Ensures that critical variables are present and raises errors if not found.

### **training.py**
- Contains your **data preparation** and **model training** logic.
- Example Functions:
  - `prepare_data_for_model(sensor_data)`: Cleans and encodes sensor data for training.
  - `train_model(sensor_data_df)`: Computes statistics (mean, std, durations) and returns a DataFrame with the model’s insights.

### **main.py**
- The **entry point** of the application. Sets up the gateway or server logic.
- Deploys or registers endpoint functions such as `create_occupancy_model_function`.
- Orchestrates calls to `fetch_all_sensor_data`, `prepare_data_for_model`, and `save_model_to_minio`.

---

## Usage

1. **Configure** environment variables (or modify `config.py`).
2. **Install dependencies** from `requirements.txt`.
3. **Run**:

   ```bash
   python main.py
   ```
   This should start your gateway service or FastAPI app.

4. **Trigger** model training or data fetching endpoints as needed (e.g., `POST /api/train`).

5. **Check logs** (`log.log` or console output) for success or errors.

---