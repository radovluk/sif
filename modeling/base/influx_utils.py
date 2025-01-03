import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from influxdb_client import InfluxDBClient

from config import (
    INFLUX_TOKEN,
    INFLUX_ORG,
    INFLUX_USER,
    INFLUX_PASS,
    BUCKET_DICT,
    PIR_BUCKETS,
    MAGNETIC_SWITCH_BUCKETS,
    BATTERY_BUCKETS
)

base_logger = logging.getLogger(__name__)

def fetch_data(bucket: str, measurement: str, field: str, start_hours: int = 24, interval_hours: int = 6) -> List[Dict[str, Any]]:
    """
    Fetch data from InfluxDB starting from `start_hours` in the past and spanning
    `interval_hours` hours into the future (towards now).

    :param bucket: Name of the InfluxDB bucket.
    :param measurement: Measurement to filter (e.g., "PIR", "battery").
    :param field: Field to fetch (e.g., "roomID", "soc").
    :param start_hours: Number of hours in the past to start fetching data.
    :param interval_hours: Number of hours to span forward from the start time.
    :return: List of fetched data as dictionaries.
    """
    now = datetime.utcnow()
    _start = now - timedelta(hours=start_hours)
    _stop = _start + timedelta(hours=interval_hours)

    with InfluxDBClient(
        url=INFLUX_TOKEN,
        org=INFLUX_ORG,
        username=INFLUX_USER,
        password=INFLUX_PASS,
        verify_ssl=False
    ) as client:
        query_api = client.query_api()

        params = {"_start": _start, "_stop": _stop}

        flux_query = f'''
            from(bucket: "{bucket}")
                |> range(start: _start, stop: _stop)
                |> filter(fn: (r) => r["_measurement"] == "{measurement}")
                |> filter(fn: (r) => r["_type"] == "sensor-value")
                |> filter(fn: (r) => r["_field"] == "{field}")
        '''

        tables = query_api.query(flux_query, params=params)

        obj = []
        for table in tables:
            for record in table.records:
                val = {
                    "sensor": BUCKET_DICT[bucket],
                    "bucket": bucket,
                    "timestamp": record["_time"].timestamp() * 1000,
                    "value": record["_value"]
                }
                if bucket in BATTERY_BUCKETS:
                    val["field"] = record["_field"]
                    val["type"] = "battery"
                else:
                    val["type"] = "sensor"

                obj.append(val)

        return obj

def fetch_data_from_buckets(
    buckets: List[str],
    measurement: str,
    fields: List[str],
    start_hours: int = 24,
    interval_hours: int = 6
) -> List[Dict[str, Any]]:
    """
    Fetch data from multiple buckets, measurements, and fields within a time interval.

    :param buckets: List of bucket names.
    :param measurement: Measurement name (e.g., "PIR", "battery").
    :param fields: List of field names (e.g., "roomID", "soc", "voltage").
    :param start_hours: Number of hours in the past to start fetching data.
    :param interval_hours: Number of hours to span forward from the start time.
    :return: Aggregated list of fetched data.
    """
    all_data = []
    for bucket in buckets:
        for field in fields:
            all_data.extend(
                fetch_data(
                    bucket=bucket,
                    measurement=measurement,
                    field=field,
                    start_hours=start_hours,
                    interval_hours=interval_hours
                )
            )
    return all_data

def fetch_all_data(start_hours: int = 24, interval_hours: int = 6) -> List[Dict[str, Any]]:
    """
    Fetch sensor data (PIR, MagneticSwitch) and battery data from different buckets.

    :param start_hours: Number of hours in the past to start fetching data.
    :param interval_hours: Number of hours to span forward from the start time.
    :return: Aggregated list of all fetched data.
    """
    all_data = []
    all_data.extend(fetch_data_from_buckets(PIR_BUCKETS, "PIR", ["roomID"], start_hours, interval_hours))
    all_data.extend(fetch_data_from_buckets(MAGNETIC_SWITCH_BUCKETS, "MagneticSwitch", ["roomID"], start_hours, interval_hours))
    all_data.extend(fetch_data_from_buckets(BATTERY_BUCKETS, "battery", ["soc", "voltage"], start_hours, interval_hours))

    return all_data

def fetch_battery_info(start_hours: int = 24, interval_hours: int = 6) -> List[Dict[str, Any]]:
    """
    Fetch only battery info (soc, voltage) within a time interval.

    :param start_hours: Number of hours in the past to start fetching data.
    :param interval_hours: Number of hours to span forward from the start time.
    :return: List of fetched battery info.
    """
    return fetch_data_from_buckets(BATTERY_BUCKETS, "battery", ["soc", "voltage"], start_hours, interval_hours)

def fetch_all_sensor_data(start_hours: int = 24, interval_hours: int = 6) -> List[Dict[str, Any]]:
    """
    Fetch all sensor data (PIR and Magnetic Switch) within the specified time range.

    :param start_hours: Number of hours in the past to start fetching data.
    :param interval_hours: Number of hours to span forward from the start time.
    :return: Aggregated list of all fetched sensor data.
    """
    all_sensor_data = []
    all_sensor_data.extend(fetch_data_from_buckets(PIR_BUCKETS, "PIR", ["roomID"], start_hours, interval_hours))
    all_sensor_data.extend(fetch_data_from_buckets(MAGNETIC_SWITCH_BUCKETS, "MagneticSwitch", ["roomID"], start_hours, interval_hours))
    return all_sensor_data

def delete_last_x_hours(bucket: str, x_hours: int):
    """
    Delete items from the specified InfluxDB bucket within the last `x_hours`.

    :param bucket: The name of the bucket from which to delete data.
    :param x_hours: Number of hours in the past to start the deletion range.
    :return: True if deletion was successful, False otherwise.
    """
    try:
        with InfluxDBClient(
            url=INFLUX_TOKEN,
            org=INFLUX_ORG,
            username=INFLUX_USER,
            password=INFLUX_PASS,
            verify_ssl=False
        ) as client:
            delete_api: DeleteApi = client.delete_api()

            # Define the time range for deletion (from now - x_hours to now)
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            start_time = now - timedelta(hours=x_hours)

            # Format times in RFC3339Nano
            # Ensure that the format ends with 'Z' to indicate UTC timezone
            start = start_time.isoformat(timespec='microseconds').replace('+00:00', 'Z')
            stop = now.isoformat(timespec='microseconds').replace('+00:00', 'Z')

            # Predicate to match all data within the time range
            predicate = '_measurement != ""'  # Adjust if you need to target specific measurements

            base_logger.info(f"Initiating deletion of items in bucket: {bucket} from {start} to {stop}")
            base_logger.debug(f"Deletion predicate: {predicate}")

            # Perform the deletion
            delete_api.delete(
                start=start,
                stop=stop,
                predicate=predicate,
                bucket=bucket,
                org=INFLUX_ORG
            )

            base_logger.info(f"Successfully deleted items from the last {x_hours} hours in bucket: {bucket}")
            return True

    except Exception as e:
        base_logger.error(f"Error deleting items from bucket '{bucket}': {e}")
        return False