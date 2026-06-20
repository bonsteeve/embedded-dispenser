"""Sensor configuration model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SensorConfig:
    """Monitoring configuration for a registered sensor."""

    group: str = "default"
    is_critical: bool = False
    polling_interval_seconds: float = 0.05
