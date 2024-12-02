from base import LocalGateway, base_logger, PeriodicTrigger, BaseEventFabric
from fastapi import Request
import json

app = LocalGateway()
base_logger.info("Gateway initiated.")

async def create_occupancy_model_function(request: Request):
    base_logger.info("Function create occupancy model called.")
    data = await request.json()
    base_logger.info(f"Function create_occupancy_model_function received data: {data}")
    base_logger.info("Now I will retrain and store the new model to Minio.")
    # TODO Retrain and store the model to Minio
    return {"status": "success"}

app.deploy(
    create_occupancy_model_function,
    name="create_occupancy_model_function",
    evts="TrainOccupancyModelEvent",
    method="POST"
)
base_logger.info("create_occupancy_model_function app deployed.")