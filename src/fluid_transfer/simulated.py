"""Software-only implementations of fluid transfer hardware."""

import asyncio

from .interfaces import FlowGate, TransferPump


class SimulatedFlowGate:
    """Simulated on/off flow gate."""

    def __init__(self) -> None:
        self._active = False

    def on(self) -> None:
        self._active = True

    def off(self) -> None:
        self._active = False

    def is_active(self) -> bool:
        return self._active


class SimulatedTransferPump:
    """
    Simulated pump that enforces a valve-before-pump interlock.

    The pump refuses to start unless the associated gate is open.
    """

    def __init__(self, gate: FlowGate) -> None:
        self._gate = gate
        self._running = False
        self._speed = 0.0

    def set_speed(self, speed: float) -> None:
        self._speed = speed

    def start(self) -> None:
        if not self._gate.is_active():
            raise RuntimeError("Pump interlock: flow gate must be open before starting pump")
        self._running = True

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def get_current_speed(self) -> float:
        return self._speed if self._running else 0.0


class SimulatedPulseFlowSensor:
    """
    Simulated pulse flow sensor driven by pump activity.

    Generates pulses asynchronously while the pump runs and the gate is open.
    """

    def __init__(
        self,
        pump: TransferPump,
        gate: FlowGate,
        pulses_per_liter: int = 1000,
        pulse_rate_at_full_speed: float = 50.0,
    ) -> None:
        self._pump = pump
        self._gate = gate
        self._pulses_per_liter = pulses_per_liter
        self._pulse_rate_at_full_speed = pulse_rate_at_full_speed
        self._pulse_count = 0
        self._pulse_limit = 0
        self._counting = False
        self._flow_rate_lpm = 0.0
        self._task: asyncio.Task[None] | None = None

    def start_counting(self, pulse_limit: int) -> None:
        self._pulse_limit = pulse_limit
        self._counting = True
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._generate_pulses())

    def stop_counting(self) -> None:
        self._counting = False
        if self._task and not self._task.done():
            self._task.cancel()

    def reset_pulse_count(self) -> None:
        self._pulse_count = 0
        self._flow_rate_lpm = 0.0

    def get_pulse_count(self) -> int:
        return self._pulse_count

    def read(self) -> float:
        return self._flow_rate_lpm

    async def _generate_pulses(self) -> None:
        try:
            while self._counting:
                if (
                    self._pump.is_running()
                    and self._gate.is_active()
                    and self._pulse_count < self._pulse_limit
                ):
                    speed_factor = max(self._pump.get_current_speed(), 1.0) / 100.0
                    rate = self._pulse_rate_at_full_speed * speed_factor * 0.1
                    pulses_this_tick = max(1, int(rate))
                    self._pulse_count = min(
                        self._pulse_count + pulses_this_tick, self._pulse_limit
                    )
                    self._flow_rate_lpm = (self._pulse_rate_at_full_speed * speed_factor * 60) / (
                        self._pulses_per_liter / 1000
                    )
                else:
                    self._flow_rate_lpm = 0.0
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass


class SimulatedOperatorTrigger:
    """Simulated operator trigger with programmatic press/release."""

    def __init__(self) -> None:
        self._pressed = False

    def read(self) -> bool:
        return self._pressed

    def press(self) -> None:
        self._pressed = True

    def release(self) -> None:
        self._pressed = False
