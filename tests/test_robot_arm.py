"""Tests for the robot arm subproject."""

import pytest

from robot_arm import MultiStageMotionOrchestrator, RobotArmConfig
from robot_arm.simulated import SimulatedMotorDriver, SimulatedPositionFeedback
from robot_arm.stages import STAGE_ORDER


@pytest.fixture
def orchestrator():
    config = RobotArmConfig.for_testing()
    feedback = SimulatedPositionFeedback(horizontal=0.0, vertical=500.0)
    motor = SimulatedMotorDriver(feedback, step_size=25.0, move_delay=0.001)
    return MultiStageMotionOrchestrator(feedback, motor, config), feedback


def test_resolve_target_returns_coordinates():
    config = RobotArmConfig()
    feedback = SimulatedPositionFeedback()
    motor = SimulatedMotorDriver(feedback)
    orch = MultiStageMotionOrchestrator(feedback, motor, config)

    target = orch.resolve_target("A2")
    assert target.horizontal == 200.0
    assert target.vertical == 200.0
    assert target.level == 1


def test_resolve_target_rejects_unknown_slot():
    feedback = SimulatedPositionFeedback()
    motor = SimulatedMotorDriver(feedback)
    orch = MultiStageMotionOrchestrator(feedback, motor)

    with pytest.raises(ValueError, match="Unknown slot"):
        orch.resolve_target("Z99")


@pytest.mark.asyncio
async def test_move_to_slot_completes_all_stages(orchestrator):
    orch, feedback = orchestrator
    result = await orch.move_to_slot("A1")

    assert result.success
    assert len(result.stage_results) == len(STAGE_ORDER)
    assert all(r.success for r in result.stage_results)

    pos = feedback.read_position()
    target = orch.resolve_target("A1")
    assert abs(pos.horizontal - target.horizontal) <= orch.config.horizontal_tolerance
    assert abs(pos.vertical - target.vertical) <= orch.config.vertical_tolerance


@pytest.mark.asyncio
async def test_stage_order_is_preserved(orchestrator):
    orch, _ = orchestrator
    result = await orch.move_to_slot("B1")

    executed = [r.stage for r in result.stage_results]
    assert executed == STAGE_ORDER


@pytest.mark.asyncio
async def test_retry_handler_corrects_position():
    from robot_arm.interfaces import MotionTarget
    from robot_arm.retry import PositioningRetryHandler

    config = RobotArmConfig.for_testing()
    feedback = SimulatedPositionFeedback(horizontal=90.0, vertical=190.0)
    motor = SimulatedMotorDriver(feedback, step_size=5.0, move_delay=0.001)
    handler = PositioningRetryHandler(feedback, motor, config)

    target = MotionTarget(slot_id="A1", horizontal=100.0, vertical=200.0, level=1)
    success, attempts = await handler.move_to_target(target)

    assert success
    assert attempts >= 0
