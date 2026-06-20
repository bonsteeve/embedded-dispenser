"""Flow gate controller with delayed close scheduling."""

import asyncio

from .config import FluidTransferConfig
from .interfaces import FlowGate


class GateController:
    """Controls a flow gate with immediate open and delayed close."""

    def __init__(self, gate: FlowGate, config: FluidTransferConfig | None = None) -> None:
        if gate is None:
            raise ValueError("Flow gate is required")
        self.gate = gate
        self.config = config or FluidTransferConfig()
        self._close_task: asyncio.Task[None] | None = None

    async def open_gate(self) -> None:
        if self._close_task and not self._close_task.done():
            self._close_task.cancel()
            self._close_task = None
        if not self.gate.is_active():
            self.gate.on()

    async def schedule_close_gate(self) -> None:
        if self._close_task and not self._close_task.done():
            self._close_task.cancel()
            try:
                await self._close_task
            except asyncio.CancelledError:
                pass
        self._close_task = asyncio.create_task(self._delayed_close())

    async def close_gate_immediately(self) -> None:
        if self._close_task and not self._close_task.done():
            self._close_task.cancel()
            try:
                await self._close_task
            except asyncio.CancelledError:
                pass
            self._close_task = None
        if self.gate.is_active():
            self.gate.off()

    async def _delayed_close(self) -> None:
        try:
            await asyncio.sleep(self.config.gate_close_delay_seconds)
            if self.gate.is_active():
                self.gate.off()
        except asyncio.CancelledError:
            pass

    def is_open(self) -> bool:
        return self.gate.is_active()

    async def cleanup(self) -> None:
        await self.close_gate_immediately()
