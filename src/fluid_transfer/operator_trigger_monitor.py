"""Debounced operator trigger monitor."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from .interfaces import OperatorTrigger


@dataclass
class OperatorTriggerState:
    """Debounced operator trigger state."""

    is_pressed: bool
    last_change_time: float
    debounce_time: float = 0.05

    def should_trigger(self, new_state: bool) -> bool:
        if new_state == self.is_pressed:
            return False
        if time.time() - self.last_change_time < self.debounce_time:
            return False
        return True


class OperatorTriggerMonitor:
    """Polls an operator trigger and fires press/release callbacks."""

    def __init__(
        self,
        trigger: OperatorTrigger,
        on_press: Callable[[], Awaitable[None]] | None = None,
        on_release: Callable[[], Awaitable[None]] | None = None,
        poll_interval: float = 0.01,
    ) -> None:
        if trigger is None:
            raise ValueError("Operator trigger is required")
        self.trigger = trigger
        self.on_press = on_press
        self.on_release = on_release
        self.poll_interval = poll_interval
        self.state = OperatorTriggerState(is_pressed=False, last_change_time=time.time())
        self._monitoring = False
        self._monitor_task: asyncio.Task[None] | None = None

    async def start_monitoring(self) -> None:
        if self._monitoring:
            return
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self) -> None:
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    async def _monitor_loop(self) -> None:
        while self._monitoring:
            try:
                current = self.trigger.read()
                if self.state.should_trigger(current):
                    old = self.state.is_pressed
                    self.state.is_pressed = current
                    self.state.last_change_time = time.time()
                    if current and not old and self.on_press:
                        await self.on_press()
                    elif not current and old and self.on_release:
                        await self.on_release()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
