"""Event-driven sensor monitoring for embedded control systems."""

from .base import MonitorableSensor
from .config import SensorConfig
from .dispatcher import EventDispatcher, SensorListener
from .events import SensorChangeEvent, SensorErrorEvent, SensorReading
from .registry import SensorRegistry
from .simulated import SimulatedSensor

__all__ = [
    "EventDispatcher",
    "MonitorableSensor",
    "SensorChangeEvent",
    "SensorConfig",
    "SensorErrorEvent",
    "SensorListener",
    "SensorReading",
    "SensorRegistry",
    "SimulatedSensor",
]
