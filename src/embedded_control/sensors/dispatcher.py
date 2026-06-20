"""Asynchronous event dispatch for sensor monitoring."""

import logging
from abc import ABC, abstractmethod
from queue import Empty, Queue
from threading import Event, Thread

from .events import SensorChangeEvent, SensorErrorEvent


class SensorListener(ABC):
    """Receives sensor change and error events."""

    @abstractmethod
    def on_sensor_change(self, event: SensorChangeEvent) -> None:
        """Handle a sensor value change."""

    @abstractmethod
    def on_sensor_error(self, event: SensorErrorEvent) -> None:
        """Handle a sensor error."""

    @abstractmethod
    def get_listener_id(self) -> str:
        """Return a unique listener identifier."""


class EventDispatcher:
    """Queues sensor events and dispatches them on a background thread."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.listeners: dict[str, list[SensorListener]] = {}
        self.global_listeners: list[SensorListener] = []
        self.event_queue: Queue[SensorChangeEvent | SensorErrorEvent] = Queue(maxsize=1000)
        self.processing_thread: Thread | None = None
        self._stop_event = Event()

    def start_processing(self) -> None:
        if self.processing_thread and self.processing_thread.is_alive():
            return
        self._stop_event.clear()
        self.processing_thread = Thread(target=self._process_events, daemon=True)
        self.processing_thread.start()

    def stop_processing(self) -> None:
        self._stop_event.set()
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)

    def enqueue(self, event: SensorChangeEvent | SensorErrorEvent) -> None:
        """Add an event to the processing queue."""
        self.event_queue.put(event)

    def register_listener(self, sensor_id: str, listener: SensorListener) -> None:
        self.listeners.setdefault(sensor_id, []).append(listener)

    def register_global_listener(self, listener: SensorListener) -> None:
        self.global_listeners.append(listener)

    def _process_events(self) -> None:
        while not self._stop_event.is_set():
            try:
                event = self.event_queue.get(timeout=0.1)
            except Empty:
                continue

            try:
                if isinstance(event, SensorChangeEvent):
                    self._dispatch_change_event(event)
                else:
                    self._dispatch_error_event(event)
            except Exception as exc:
                self.logger.error("Error processing sensor event: %s", exc)
            finally:
                self.event_queue.task_done()

    def _dispatch_change_event(self, event: SensorChangeEvent) -> None:
        for listener in self.listeners.get(event.sensor_id, []):
            self._safe_call(listener.on_sensor_change, event, listener.get_listener_id())
        for listener in self.global_listeners:
            self._safe_call(listener.on_sensor_change, event, listener.get_listener_id())

    def _dispatch_error_event(self, event: SensorErrorEvent) -> None:
        for listener in self.listeners.get(event.sensor_id, []):
            self._safe_call(listener.on_sensor_error, event, listener.get_listener_id())
        for listener in self.global_listeners:
            self._safe_call(listener.on_sensor_error, event, listener.get_listener_id())

    def _safe_call(self, callback, event, listener_id: str) -> None:
        try:
            callback(event)
        except Exception as exc:
            self.logger.error("Listener %s failed: %s", listener_id, exc)
