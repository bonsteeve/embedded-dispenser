"""Sensor event and reading data types."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class SensorReading:
    """Immutable snapshot of a single sensor read."""

    sensor_id: str
    timestamp: datetime
    value: Any
    is_valid: bool
    error_message: str | None = None


@dataclass
class SensorChangeEvent:
    """Emitted when a sensor value changes beyond its threshold."""

    sensor_id: str
    old_reading: SensorReading
    new_reading: SensorReading
    change_magnitude: float
    change_type: str


@dataclass
class SensorErrorEvent:
    """Emitted when a sensor read fails."""

    sensor_id: str
    error_type: str
    error_message: str
    timestamp: datetime
    last_valid_reading: SensorReading | None = None
