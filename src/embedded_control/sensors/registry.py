"""Central registry for monitorable sensors."""

from .base import MonitorableSensor
from .config import SensorConfig


class SensorRegistry:
    """Registers sensors, groups them, and exposes lookup helpers."""

    def __init__(self) -> None:
        self.sensors: dict[str, MonitorableSensor] = {}
        self.sensor_groups: dict[str, list[str]] = {}
        self.sensor_configs: dict[str, SensorConfig] = {}

    def register(self, sensor: MonitorableSensor, config: SensorConfig) -> None:
        sensor_id = sensor.get_sensor_id()
        self.sensors[sensor_id] = sensor
        self.sensor_configs[sensor_id] = config
        self.sensor_groups.setdefault(config.group, []).append(sensor_id)

    def get_sensor(self, sensor_id: str) -> MonitorableSensor | None:
        return self.sensors.get(sensor_id)

    def get_sensors_by_group(self, group: str) -> list[MonitorableSensor]:
        sensor_ids = self.sensor_groups.get(group, [])
        return [self.sensors[sensor_id] for sensor_id in sensor_ids if sensor_id in self.sensors]

    def get_critical_sensors(self) -> list[MonitorableSensor]:
        return [
            sensor
            for sensor_id, sensor in self.sensors.items()
            if self.sensor_configs[sensor_id].is_critical
        ]

    def get_all_sensors(self) -> list[MonitorableSensor]:
        return list(self.sensors.values())

    def get_sensor_config(self, sensor_id: str) -> SensorConfig | None:
        return self.sensor_configs.get(sensor_id)
