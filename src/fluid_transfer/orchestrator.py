"""Coordinates state machine, hardware controllers, and monitors for fluid transfer."""

from collections.abc import Awaitable, Callable
from typing import Any

from embedded_control.process import (
    GatedTransferStateMachine,
    ProcessRequest,
    ProcessState,
)

from .config import FluidTransferConfig
from .flow_sensor_monitor import FlowSensorMonitor, FlowSensorState
from .gate_controller import GateController
from .interfaces import FlowGate, OperatorTrigger, PulseFlowSensor, TransferPump
from .operator_trigger_monitor import OperatorTriggerMonitor
from .pump_controller import PumpController
from .request_parser import TransferRequestParser

StatusCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class FluidTransferOrchestrator:
    """
    End-to-end fluid transfer coordinator.

    Wires the gated transfer state machine to pump, gate, flow sensor,
    and operator trigger controllers — the same layering used in production
  dispensing systems, but with protocol-based hardware that can be swapped
    for real GPIO drivers.
    """

    def __init__(
        self,
        pump: TransferPump,
        gate: FlowGate,
        flow_sensor: PulseFlowSensor,
        operator_trigger: OperatorTrigger,
        config: FluidTransferConfig | None = None,
        on_status_update: StatusCallback | None = None,
    ) -> None:
        self.config = config or FluidTransferConfig()
        self.parser = TransferRequestParser(self.config)
        self.on_status_update = on_status_update

        self.state_machine = GatedTransferStateMachine(
            config=self.config.to_process_config(),
            on_state_change=self._on_state_change,
        )
        self.gate_controller = GateController(gate, self.config)
        self.pump_controller = PumpController(pump, self.config)
        self.operator_monitor = OperatorTriggerMonitor(
            operator_trigger,
            on_press=self._on_operator_pressed,
            on_release=self._on_operator_released,
        )
        self.flow_monitor = FlowSensorMonitor(
            flow_sensor,
            config=self.config,
            on_progress=self._on_flow_progress,
            on_target_reached=self._on_target_reached,
            on_low_flow_detected=self._on_low_flow_detected,
        )
        self._active_volume = 0.0

    async def start_transfer(self, message: str) -> dict[str, Any]:
        """Parse a request and begin waiting for operator confirmation."""
        parsed = self.parser.parse(message)
        request = ProcessRequest(
            request_id=parsed["request_id"],
            target_quantity=parsed["volume"],
            target_slot=parsed["slot"],
        )

        started = await self.state_machine.start(request)
        if not started:
            return {
                "type": "error",
                "error": "Transfer already in progress",
                "request_id": parsed["request_id"],
            }

        self._active_volume = parsed["volume"]
        await self.operator_monitor.start_monitoring()
        await self.flow_monitor.start_monitoring(parsed["volume"])

        return {
            "type": "acknowledgment",
            "request_id": parsed["request_id"],
            "status": "request_received",
            "slot": parsed["slot"],
            "message": (
                f"Transfer of {parsed['volume']} units to slot {parsed['slot']} accepted. "
                "Engage operator trigger to begin."
            ),
        }

    async def abort_transfer(self, request_id: str | None = None) -> dict[str, Any]:
        aborted = await self.state_machine.abort()
        if not aborted:
            return {"type": "error", "error": "No active transfer to abort"}

        await self._shutdown_hardware()
        await self.state_machine.reset()

        return {
            "type": "acknowledgment",
            "request_id": request_id,
            "status": "aborted",
        }

    async def _on_operator_pressed(self) -> None:
        await self.gate_controller.open_gate()
        await self.state_machine.on_operator_pressed()

        if self.state_machine.state == ProcessState.ACTIVE:
            started = await self.pump_controller.start_pump()
            if not started:
                await self.state_machine.error("Pump failed to start — gate interlock")
                await self._shutdown_hardware()

    async def _on_operator_released(self) -> None:
        await self.pump_controller.stop_pump()
        await self.gate_controller.schedule_close_gate()
        await self.flow_monitor.pause_monitoring()
        await self.state_machine.on_operator_released()

    async def _on_flow_progress(self, state: FlowSensorState) -> None:
        await self.state_machine.update_progress(state.volume)
        await self._emit_status("progress", {"volume": state.volume})

    async def _on_target_reached(self) -> None:
        await self.pump_controller.stop_pump()
        await self.gate_controller.close_gate_immediately()
        await self.state_machine.update_progress(self._active_volume)
        await self._finalize()

    async def _on_low_flow_detected(self, state: FlowSensorState) -> None:
        await self.pump_controller.stop_pump()
        await self.gate_controller.close_gate_immediately()
        await self.state_machine.complete_early(state.flow_rate_lpm, "low_throughput")
        await self._finalize()

    async def _on_state_change(
        self,
        old_state: ProcessState,
        new_state: ProcessState,
        request: ProcessRequest | None,
    ) -> None:
        terminal = {
            ProcessState.COMPLETED,
            ProcessState.ERROR,
            ProcessState.TIMEOUT,
            ProcessState.ABORTED,
        }
        if new_state in terminal:
            await self._shutdown_hardware()
            if new_state != ProcessState.ABORTED:
                await self.state_machine.reset()

        await self._emit_status(
            "state_change",
            {
                "from": old_state.value,
                "to": new_state.value,
                "request_id": request.request_id if request else None,
            },
        )

    async def _finalize(self) -> None:
        await self.operator_monitor.stop_monitoring()
        await self.flow_monitor.cleanup()

    async def _shutdown_hardware(self) -> None:
        await self.pump_controller.emergency_stop()
        await self.gate_controller.cleanup()
        await self.operator_monitor.stop_monitoring()
        await self.flow_monitor.cleanup()

    async def _emit_status(self, event: str, data: dict[str, Any]) -> None:
        if self.on_status_update:
            payload = {"type": "transfer_status", "event": event, **data}
            payload.update(self.state_machine.get_status())
            result = self.on_status_update(payload)
            if hasattr(result, "__await__"):
                await result

    def get_status(self) -> dict[str, Any]:
        return self.state_machine.get_status()
