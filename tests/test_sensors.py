"""Tests for sensor monitoring components."""

from datetime import datetime, timezone

from embedded_control.sensors import (
    EventDispatcher,
    SensorChangeEvent,
    SensorConfig,
    SensorListener,
    SensorReading,
    SensorRegistry,
    SimulatedSensor,
)


class RecordingListener(SensorListener):
    def __init__(self) -> None:
        self.changes: list[SensorChangeEvent] = []
        self.errors: list = []

    def on_sensor_change(self, event: SensorChangeEvent) -> None:
        self.changes.append(event)

    def on_sensor_error(self, event) -> None:
        self.errors.append(event)

    def get_listener_id(self) -> str:
        return "recording-listener"


def test_registry_groups_and_critical_lookup() -> None:
    registry = SensorRegistry()
    temp = SimulatedSensor("temp-1", sensor_type="temperature", critical=True)
    flow = SimulatedSensor("flow-1", sensor_type="flow", critical=False)

    registry.register(temp, SensorConfig(group="thermal", is_critical=True))
    registry.register(flow, SensorConfig(group="flow", is_critical=False))

    assert len(registry.get_sensors_by_group("thermal")) == 1
    assert len(registry.get_critical_sensors()) == 1
    assert registry.get_sensor("temp-1") is temp


def test_dispatcher_delivers_change_events() -> None:
    dispatcher = EventDispatcher()
    listener = RecordingListener()
    dispatcher.register_global_listener(listener)
    dispatcher.start_processing()

    old = SensorReading("temp-1", datetime.now(timezone.utc), 20.0, True)
    new = SensorReading("temp-1", datetime.now(timezone.utc), 25.0, True)
    event = SensorChangeEvent("temp-1", old, new, 5.0, "threshold")
    dispatcher.enqueue(event)

    import time

    time.sleep(0.3)
    dispatcher.stop_processing()

    assert len(listener.changes) == 1
    assert listener.changes[0].change_magnitude == 5.0


def test_simulated_sensor_reads_configured_value() -> None:
    sensor = SimulatedSensor("sim-1", initial_value=42.0)
    reading = sensor.read_value()

    assert reading.sensor_id == "sim-1"
    assert reading.value == 42.0
    assert reading.is_valid

    sensor.set_value(50.0)
    assert sensor.read_value().value == 50.0
