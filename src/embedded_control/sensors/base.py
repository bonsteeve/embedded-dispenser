"""Abstract interface for monitorable sensors."""

from abc import ABC, abstractmethod

from .events import SensorReading


class MonitorableSensor(ABC):
    """Contract for sensors integrated with the monitoring framework."""

    @abstractmethod
    def get_sensor_id(self) -> str:
        """Return a unique sensor identifier."""

    @abstractmethod
    def read_value(self) -> SensorReading:
        """Read and return the current sensor value."""

    @abstractmethod
    def get_sensor_type(self) -> str:
        """Return a descriptive sensor type string."""

    @abstractmethod
    def get_change_threshold(self) -> float:
        """Return the minimum change magnitude that triggers an event."""

    @abstractmethod
    def is_critical(self) -> bool:
        """Return True when this sensor is safety-critical."""

    def get_polling_interval(self) -> float:
        """Return the recommended polling interval in seconds."""
        return 0.05

    def validate_reading(self, reading: SensorReading) -> bool:
        """Return True when the reading is considered valid."""
        return reading.is_valid
