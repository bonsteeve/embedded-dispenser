"""Tests for the fluid transfer subproject."""

import asyncio
import json

import pytest

from fluid_transfer import FluidTransferConfig, FluidTransferOrchestrator
from fluid_transfer.request_parser import TransferRequestParser
from fluid_transfer.simulated import (
    SimulatedFlowGate,
    SimulatedOperatorTrigger,
    SimulatedPulseFlowSensor,
    SimulatedTransferPump,
)


@pytest.fixture
def hardware():
    config = FluidTransferConfig.for_testing()
    gate = SimulatedFlowGate()
    pump = SimulatedTransferPump(gate)
    flow_sensor = SimulatedPulseFlowSensor(pump, gate, pulses_per_liter=100)
    trigger = SimulatedOperatorTrigger()
    return config, gate, pump, flow_sensor, trigger


@pytest.fixture
def orchestrator(hardware):
    config, gate, pump, flow_sensor, trigger = hardware
    return FluidTransferOrchestrator(
        pump=pump,
        gate=gate,
        flow_sensor=flow_sensor,
        operator_trigger=trigger,
        config=config,
    )


def test_request_parser_validates_transfer():
    parser = TransferRequestParser()
    result = parser.parse(
        json.dumps({"action": "transfer", "volume": 50, "request_id": "r1", "slot": "A1"})
    )
    assert result["volume"] == 50.0
    assert result["slot"] == "A1"


def test_request_parser_rejects_invalid_slot():
    parser = TransferRequestParser()
    with pytest.raises(ValueError, match="Invalid slot"):
        parser.parse(
            json.dumps({"action": "transfer", "volume": 50, "request_id": "r1", "slot": "Z9"})
        )


def test_pump_interlock_requires_open_gate(hardware):
    _, gate, pump, _, _ = hardware
    with pytest.raises(RuntimeError, match="interlock"):
        pump.start()
    gate.on()
    pump.start()
    assert pump.is_running()


@pytest.mark.asyncio
async def test_full_transfer_flow(orchestrator, hardware):
    _, _, _, _, trigger = hardware

    ack = await orchestrator.start_transfer(
        json.dumps({"action": "transfer", "volume": 30, "request_id": "t1", "slot": "A2"})
    )
    assert ack["type"] == "acknowledgment"

    trigger.press()
    await asyncio.sleep(1.5)

    status = orchestrator.get_status()
    assert status["state"] in {"completed", "active", "waiting_operator"}


@pytest.mark.asyncio
async def test_abort_stops_active_transfer(orchestrator, hardware):
    _, _, _, _, trigger = hardware

    await orchestrator.start_transfer(
        json.dumps({"action": "transfer", "volume": 100, "request_id": "t2", "slot": "A1"})
    )
    trigger.press()
    await asyncio.sleep(0.2)

    result = await orchestrator.abort_transfer("t2")
    assert result["status"] == "aborted"
