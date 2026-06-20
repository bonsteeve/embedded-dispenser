"""Pump controller with speed validation and interlock handling."""

from .config import FluidTransferConfig
from .interfaces import TransferPump


class PumpController:
    """Manages pump start/stop lifecycle during transfer operations."""

    def __init__(self, pump: TransferPump, config: FluidTransferConfig | None = None) -> None:
        if pump is None:
            raise ValueError("Transfer pump is required")
        self.pump = pump
        self.config = config or FluidTransferConfig()
        self._is_running = False

    async def start_pump(self, speed: float | None = None) -> bool:
        try:
            if self._is_running:
                return True

            pump_speed = speed if speed is not None else self.config.pump_default_speed
            pump_speed = max(
                self.config.pump_min_speed,
                min(self.config.pump_max_speed, pump_speed),
            )

            self.pump.set_speed(pump_speed)
            self.pump.start()
            self._is_running = self.pump.is_running()
            return self._is_running
        except RuntimeError:
            return False

    async def stop_pump(self) -> None:
        try:
            self.pump.stop()
        finally:
            self._is_running = False

    def is_running(self) -> bool:
        self._is_running = self.pump.is_running()
        return self._is_running

    async def emergency_stop(self) -> None:
        try:
            self.pump.stop()
        finally:
            self._is_running = False
