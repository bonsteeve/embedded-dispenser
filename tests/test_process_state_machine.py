"""Tests for the gated transfer state machine."""

import asyncio

import pytest

from embedded_control.process import (
    GatedTransferStateMachine,
    ProcessConfig,
    ProcessRequest,
    ProcessState,
)


@pytest.fixture
def machine() -> GatedTransferStateMachine:
    return GatedTransferStateMachine(config=ProcessConfig.for_testing())


@pytest.mark.asyncio
async def test_start_transitions_to_waiting_operator(machine: GatedTransferStateMachine) -> None:
    request = ProcessRequest(request_id="req-1", target_quantity=100.0, target_slot="A1")
    started = await machine.start(request)

    assert started
    assert machine.state == ProcessState.WAITING_OPERATOR
    assert machine.current_request == request


@pytest.mark.asyncio
async def test_rejects_second_start_while_busy(machine: GatedTransferStateMachine) -> None:
    request = ProcessRequest(request_id="req-1", target_quantity=100.0, target_slot="A1")
    await machine.start(request)
    second = await machine.start(
        ProcessRequest(request_id="req-2", target_quantity=50.0, target_slot="B2")
    )

    assert not second
    assert machine.current_request.request_id == "req-1"


@pytest.mark.asyncio
async def test_operator_flow_to_completion(machine: GatedTransferStateMachine) -> None:
    await machine.start(ProcessRequest(request_id="req-1", target_quantity=10.0, target_slot="A1"))
    await machine.on_operator_pressed()
    assert machine.state == ProcessState.ACTIVE

    await machine.update_progress(10.0)
    assert machine.state == ProcessState.COMPLETED
    assert machine.completion_reason == "target_reached"


@pytest.mark.asyncio
async def test_pause_and_resume(machine: GatedTransferStateMachine) -> None:
    await machine.start(ProcessRequest(request_id="req-1", target_quantity=10.0, target_slot="A1"))
    await machine.on_operator_pressed()
    await machine.on_operator_released()

    assert machine.state == ProcessState.PAUSED
    assert machine.progress is not None
    assert machine.progress.pause_count == 1

    await machine.on_operator_pressed()
    assert machine.state == ProcessState.ACTIVE


@pytest.mark.asyncio
async def test_abort_from_active_state(machine: GatedTransferStateMachine) -> None:
    await machine.start(ProcessRequest(request_id="req-1", target_quantity=10.0, target_slot="A1"))
    await machine.on_operator_pressed()

    aborted = await machine.abort("operator_cancel")
    assert aborted
    assert machine.state == ProcessState.ABORTED
    assert machine.abort_reason == "operator_cancel"


@pytest.mark.asyncio
async def test_operator_wait_timeout(machine: GatedTransferStateMachine) -> None:
    await machine.start(ProcessRequest(request_id="req-1", target_quantity=10.0, target_slot="A1"))
    await asyncio.sleep(1.2)

    assert machine.state == ProcessState.TIMEOUT
    assert machine.timeout_reason == "operator_wait"
