"""Motion stage definitions and progress reporting types."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class MotionStage(Enum):
    """Ordered stages in a multi-axis positioning sequence."""

    RETRACT = "retract"
    CLEARANCE = "clearance"
    VERTICAL_ALIGN = "vertical_align"
    HORIZONTAL_ALIGN = "horizontal_align"
    FINAL_APPROACH = "final_approach"


STAGE_ORDER: list[MotionStage] = [
    MotionStage.RETRACT,
    MotionStage.CLEARANCE,
    MotionStage.VERTICAL_ALIGN,
    MotionStage.HORIZONTAL_ALIGN,
    MotionStage.FINAL_APPROACH,
]


@dataclass
class StageResult:
    """Outcome of a single motion stage."""

    stage: MotionStage
    success: bool
    duration: float
    skipped: bool = False
    error_message: str | None = None
    details: dict[str, Any] | None = None


class StageStatus(Enum):
    """Lifecycle status for progress callbacks."""

    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageProgressInfo:
    """Progress notification payload."""

    stage: MotionStage
    status: StageStatus
    stage_result: StageResult | None = None


class MotionProgressCallback(Protocol):
    """Observer for stage-level progress events."""

    def on_stage_progress(self, progress_info: StageProgressInfo) -> None: ...


class NoOpProgressCallback:
    """Default callback that discards progress events."""

    def on_stage_progress(self, progress_info: StageProgressInfo) -> None:
        pass
