"""Flow sensor monitor with volume tracking and low-flow detection."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from .config import FluidTransferConfig
from .interfaces import PulseFlowSensor


@dataclass
class FlowSensorState:
    """Current flow sensor readings and monitoring flags."""

    pulse_count: int = 0
    volume: float = 0.0
    flow_rate_lpm: float = 0.0
    target_pulses: int = 0
    is_monitoring: bool = False
    low_flow_detected: bool = False


class FlowSensorMonitor:
    """Tracks transferred volume via pulse counting."""

    def __init__(
        self,
        flow_sensor: PulseFlowSensor,
        config: FluidTransferConfig | None = None,
        on_progress: Callable[[FlowSensorState], Awaitable[None]] | None = None,
        on_target_reached: Callable[[], Awaitable[None]] | None = None,
        on_low_flow_detected: Callable[[FlowSensorState], Awaitable[None]] | None = None,
    ) -> None:
        if flow_sensor is None:
            raise ValueError("Flow sensor is required")
        self.flow_sensor = flow_sensor
        self.config = config or FluidTransferConfig()
        self.on_progress = on_progress
        self.on_target_reached = on_target_reached
        self.on_low_flow_detected = on_low_flow_detected
        self.state = FlowSensorState()
        self._monitor_task: asyncio.Task[None] | None = None
        self._low_flow_start: float | None = None

    async def start_monitoring(self, target_volume: float) -> None:
        if self.state.is_monitoring:
            return

        self.state.target_pulses = int(
            (target_volume / 1000.0) * self.config.pulses_per_liter
        )
        self.flow_sensor.stop_counting()
        self.flow_sensor.reset_pulse_count()
        self.flow_sensor.start_counting(self.state.target_pulses)

        self.state = FlowSensorState(
            target_pulses=self.state.target_pulses,
            is_monitoring=True,
        )
        self._low_flow_start = None
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self) -> None:
        self.state.is_monitoring = False
        self.flow_sensor.stop_counting()
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    async def pause_monitoring(self) -> None:
        if not self.state.is_monitoring:
            return
        self.state.pulse_count = self.flow_sensor.get_pulse_count()
        self.state.volume = self._pulses_to_volume(self.state.pulse_count)
        await self.stop_monitoring()

    async def resume_monitoring(self) -> None:
        if self.state.is_monitoring or self.state.target_pulses == 0:
            return
        self.state.is_monitoring = True
        self.flow_sensor.start_counting(self.state.target_pulses)
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self) -> None:
        last_progress = time.time()
        while self.state.is_monitoring:
            try:
                pulses = self.flow_sensor.get_pulse_count()
                self.state.pulse_count = pulses
                self.state.volume = self._pulses_to_volume(pulses)
                self.state.flow_rate_lpm = self.flow_sensor.read()
                now = time.time()

                if pulses > 0 and self.state.flow_rate_lpm < self.config.min_flow_rate_lpm:
                    if self._low_flow_start is None:
                        self._low_flow_start = now
                    elif now - self._low_flow_start >= self.config.low_flow_timeout_seconds:
                        self.state.low_flow_detected = True
                        self.state.is_monitoring = False
                        if self.on_low_flow_detected:
                            await self.on_low_flow_detected(self.state)
                        break
                else:
                    self._low_flow_start = None

                if pulses >= self.state.target_pulses:
                    self.state.is_monitoring = False
                    if self.on_target_reached:
                        await self.on_target_reached()
                    break

                if now - last_progress >= self.config.flow_update_interval_seconds:
                    if self.on_progress:
                        await self.on_progress(self.state)
                    last_progress = now

                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break

    def _pulses_to_volume(self, pulses: int) -> float:
        return (pulses / self.config.pulses_per_liter) * 1000.0

    async def cleanup(self) -> None:
        await self.stop_monitoring()
        self.flow_sensor.reset_pulse_count()
