"""Executes individual motion stages."""

import logging
import time

from .config import RobotArmConfig
from .interfaces import MotionTarget, MotorDriver, PositionFeedback
from .retry import PositioningRetryHandler
from .stages import MotionStage, StageResult


class MotionStageExecutor:
    """Runs each stage of the positioning pipeline."""

    def __init__(
        self,
        feedback: PositionFeedback,
        motor: MotorDriver,
        config: RobotArmConfig | None = None,
    ) -> None:
        self.feedback = feedback
        self.motor = motor
        self.config = config or RobotArmConfig()
        self.retry_handler = PositioningRetryHandler(feedback, motor, self.config)
        self.logger = logging.getLogger(__name__)

    async def execute_stage(self, stage: MotionStage, target: MotionTarget) -> StageResult:
        start = time.perf_counter()

        try:
            if stage == MotionStage.RETRACT:
                success = await self._retract()
            elif stage == MotionStage.CLEARANCE:
                success = await self._move_to_clearance(target)
            elif stage in {MotionStage.VERTICAL_ALIGN, MotionStage.HORIZONTAL_ALIGN}:
                success, _ = await self.retry_handler.move_to_target(target)
            elif stage == MotionStage.FINAL_APPROACH:
                success = await self._final_approach(target)
            else:
                return StageResult(
                    stage=stage,
                    success=False,
                    duration=0.0,
                    error_message="Unknown stage",
                )

            duration = time.perf_counter() - start
            return StageResult(stage=stage, success=success, duration=duration)
        except Exception as exc:
            duration = time.perf_counter() - start
            return StageResult(
                stage=stage,
                success=False,
                duration=duration,
                error_message=str(exc),
            )

    async def _retract(self) -> bool:
        """Move to a safe retracted vertical position."""
        pos = self.feedback.read_position()
        safe_vertical = min(pos.vertical, 50.0)
        return await self.motor.move_vertical(safe_vertical, self.config.default_speed)

    async def _move_to_clearance(self, target: MotionTarget) -> bool:
        """Move to shared clearance height before horizontal travel."""
        clearance_vertical = 150.0 if target.level == 1 else 350.0
        return await self.motor.move_vertical(clearance_vertical, self.config.default_speed)

    async def _final_approach(self, target: MotionTarget) -> bool:
        """Precision final approach to target coordinates."""
        success, _ = await self.retry_handler.move_to_target(target)
        return success
