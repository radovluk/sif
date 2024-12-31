import os
import urllib3

from abc import ABC, abstractmethod
from typing import Tuple, Any


class BaseEventFabric(ABC):
    def __init__(self):
        self.scheduler = os.environ.get(
            "SCH_SERVICE_NAME", "http://localhost:8080")
        if not self.scheduler.startswith("http://"):
            self.scheduler = f"http://{self.scheduler}"

        print(f"Relying on the scheduler at {self.scheduler}")
        super(BaseEventFabric, self).__init__()

    @abstractmethod
    def call(self, *args, **kwargs) -> Tuple[str, Any]:
        """
        Custom implementation to handle event invocations. Each child event
        must adhere to this structure so events are properly propagated to the
        SIF-edge scheduler

        :returns: once the callback finished, it must return the event's name and corresponding data
        :rtype: Tuple[str, Any]
        """
        raise NotImplementedError("Implement the 'call' method in your class")

    def __call__(self, *args, **kwargs):
        evt_name, data = self.call(*args, **kwargs)
        try:
            http = urllib3.PoolManager()
            res = http.request('POST', f"{self.scheduler}/api/event",
                               json=dict(name=evt_name, data=data), retries=urllib3.Retry(5))
            if res.status >= 300:
                print(
                    f"Failure to send EventRequest to the scheduler because {res.reason}")
        except Exception as err:
            print("Failure during request because:")
            print(err)


class ExampleEventFabric(BaseEventFabric):

    def __init__(self):
        super(ExampleEventFabric, self).__init__()

    def call(self, *args, **kwargs):
        return "GenEvent", None

class TrainOccupancyModelEvent(BaseEventFabric):
    """
    Event class responsible for triggering an occupancy model retraining.
    """
    def call(self, *args, **kwargs):
        """
        Execute when the event is triggered.

        :return: Tuple of (event_name, data_dict)
        """
        event_name = "TrainOccupancyModelEvent"
        data = {"message": "Retraining the occupancy model"}
        logger.info(f"Event generated: {event_name} with data {data}")
        return event_name, data

class CheckEmergencyEvent(BaseEventFabric):
    """
    Event class responsible for checking emergency conditions.
    """
    def call(self, *args, **kwargs):
        """
        Execute when the event is triggered.

        :return: Tuple of (event_name, data_dict)
        """
        event_name = "CheckEmergencyEvent"
        data = {"message": "Checking for emergencies"}
        logger.info(f"Event generated: {event_name} with data {data}")
        return event_name, data

class EmergencyEvent(BaseEventFabric):
    """
    Event class triggered when an emergency condition is detected.
    """
    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def call(self, *args, **kwargs):
        """
        Execute when an emergency condition is detected.

        :return: Tuple of (event_name, data_dict)
        """
        event_name = "EmergencyEvent"
        data = {"message": self.message}
        logger.info(f"Event generated: {event_name} with message {self.message}")
        return event_name, data

class TrainMotionModelEvent(BaseEventFabric):
    """
    Event class responsible for triggering an motion model retraining.
    """
    def call(self, *args, **kwargs):
        """
        Execute when the event is triggered.

        :return: Tuple of (event_name, data_dict)
        """
        event_name = "TrainMotionModelEvent"
        data = {"message": "Retraining the motion model"}
        logger.info(f"Event generated: {event_name} with data {data}")
        return event_name, data

class AnalyzeMotionEvent(BaseEventFabric):
    """
    Event class responsible for triggering an motion model analysis.
    """
    def call(self, *args, **kwargs):
        """
        Execute when the event is triggered.

        :return: Tuple of (event_name, data_dict)
        """
        event_name = "AnalyzeMotionEvent"
        data = {"message": "Analysis of the motion model"}
        logger.info(f"Event generated: {event_name} with data {data}")
        return event_name, data