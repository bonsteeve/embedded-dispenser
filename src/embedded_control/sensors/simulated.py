"""Software-only sensor for demonstrations and unit tests."""

from datetime import datetime, timezone

from .base import MonitorableSensor
from .events import SensorReading


class SimulatedSensor(MonitorableSensor):
    """In-memory sensor with configurable value and threshold."""

    def __init__(
        self,
        sensor_id: str,
        sensor_type: str = "simulated",
        initial_value: float = 0.0,
        change_threshold: float = 0.1,
        critical: bool = False,
    ) -> None:
        self._sensor_id = sensor_id
        self._sensor_type = sensor_type
        self._value = initial_value
        self._change_threshold = change_threshold
        self._critical = critical

    def get_sensor_id(self) -> str:
        return self._sensor_id

    def get_sensor_type(self) -> str:
        return self._sensor_type

    def get_change_threshold(self) -> float:
        return self._change_threshold

    def is_critical(self) -> bool:
        return self._critical

    def set_value(self, value: float) -> None:
        """Update the simulated reading."""
        self._value = value

    def read_value(self) -> SensorReading:
        return SensorReading(
            sensor_id=self._sensor_id,
            timestamp=datetime.now(timezone.utc),
            value=self._value,
            is_valid=True,
        )
