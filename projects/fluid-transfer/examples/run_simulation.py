"""End-to-end fluid transfer simulation."""

import asyncio
import json

from fluid_transfer import FluidTransferConfig, FluidTransferOrchestrator
from fluid_transfer.simulated import (
    SimulatedFlowGate,
    SimulatedOperatorTrigger,
    SimulatedPulseFlowSensor,
    SimulatedTransferPump,
)


async def main() -> None:
    config = FluidTransferConfig.for_testing()
    gate = SimulatedFlowGate()
    pump = SimulatedTransferPump(gate)
    flow_sensor = SimulatedPulseFlowSensor(pump, gate, pulses_per_liter=config.pulses_per_liter)
    trigger = SimulatedOperatorTrigger()

    status_log: list[dict] = []

    async def on_status(payload: dict) -> None:
        status_log.append(payload)
        print(f"  STATUS: {json.dumps(payload, default=str)}")

    orchestrator = FluidTransferOrchestrator(
        pump=pump,
        gate=gate,
        flow_sensor=flow_sensor,
        operator_trigger=trigger,
        config=config,
        on_status_update=on_status,
    )

    request = json.dumps(
        {"action": "transfer", "volume": 50.0, "request_id": "demo-1", "slot": "A1"}
    )

    print("1. Starting transfer...")
    ack = await orchestrator.start_transfer(request)
    print(f"   ACK: {json.dumps(ack)}")

    print("2. Operator trigger pressed — pump and gate activate")
    trigger.press()
    await asyncio.sleep(0.5)

    print("3. Waiting for target volume...")
    await asyncio.sleep(2.0)

    print(f"\nDone. Final status: {json.dumps(orchestrator.get_status())}")
    print(f"Events received: {len(status_log)}")


if __name__ == "__main__":
    asyncio.run(main())
