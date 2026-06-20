"""Multi-stage motion orchestrator for two-axis positioning."""

import logging
import time
from dataclasses import dataclass

from .config import RobotArmConfig
from .interfaces import MotionTarget, MotorDriver, PositionFeedback
from .stage_executor import MotionStageExecutor
from .stages import (
    STAGE_ORDER,
    MotionProgressCallback,
    MotionStage,
    NoOpProgressCallback,
    StageProgressInfo,
    StageResult,
    StageStatus,
)


@dataclass
class MotionResult:
    """Outcome of a complete multi-stage motion sequence."""

    success: bool
    target_slot: str
    total_duration: float
    stage_results: list[StageResult]
    error_message: str | None = None


class MultiStageMotionOrchestrator:
    """
    Coordinates the full positioning pipeline.

    Executes stages in order — retract, clearance, vertical align,
    horizontal align, final approach — with progress callbacks and
    structured per-stage results. This is the generalized form of a
    production move-to-target controller.
    """

    def __init__(
        self,
        feedback: PositionFeedback,
        motor: MotorDriver,
        config: RobotArmConfig | None = None,
        progress_callback: MotionProgressCallback | None = None,
    ) -> None:
        self.config = config or RobotArmConfig()
        self.progress_callback = progress_callback or NoOpProgressCallback()
        self.stage_executor = MotionStageExecutor(feedback, motor, self.config)
        self.logger = logging.getLogger(__name__)

    def resolve_target(self, slot_id: str) -> MotionTarget:
        if slot_id not in self.config.slots:
            raise ValueError(f"Unknown slot: {slot_id}")
        horizontal, vertical, level = self.config.slots[slot_id]
        return MotionTarget(slot_id=slot_id, horizontal=horizontal, vertical=vertical, level=level)

    async def move_to_slot(self, slot_id: str) -> MotionResult:
        """Execute the full stage sequence to reach a target slot."""
        target = self.resolve_target(slot_id)
        stage_results: list[StageResult] = []
        start = time.perf_counter()

        for stage in STAGE_ORDER:
            self._notify(stage, StageStatus.IN_PROGRESS)
            result = await self.stage_executor.execute_stage(stage, target)
            stage_results.append(result)

            if result.success:
                self._notify(stage, StageStatus.SUCCESS, result)
            else:
                self._notify(stage, StageStatus.FAILED, result)
                await self.stage_executor.motor.stop_all()
                return MotionResult(
                    success=False,
                    target_slot=slot_id,
                    total_duration=time.perf_counter() - start,
                    stage_results=stage_results,
                    error_message=result.error_message or f"Stage {stage.value} failed",
                )

        return MotionResult(
            success=True,
            target_slot=slot_id,
            total_duration=time.perf_counter() - start,
            stage_results=stage_results,
        )

    def _notify(
        self,
        stage: MotionStage,
        status: StageStatus,
        stage_result: StageResult | None = None,
    ) -> None:
        try:
            self.progress_callback.on_stage_progress(
                StageProgressInfo(stage=stage, status=status, stage_result=stage_result)
            )
        except Exception as exc:
            self.logger.warning("Progress callback failed: %s", exc)
