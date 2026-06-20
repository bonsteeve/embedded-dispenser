"""Hardware abstraction protocols for robot arm control."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class AxisPosition:
    """Feedback position for a two-axis system."""

    horizontal: float
    vertical: float


@dataclass
class MotionTarget:
    """Target coordinates for a positioning operation."""

    slot_id: str
    horizontal: float
    vertical: float
    level: int = 1


class PositionFeedback(Protocol):
    """Reads current axis positions (e.g. ADC, encoder)."""

    def read_position(self) -> AxisPosition: ...


class MotorDriver(Protocol):
    """Executes axis movements."""

    async def move_vertical(self, target: float, speed: float) -> bool: ...
    async def move_horizontal(self, target: float, speed: float) -> bool: ...
    async def stop_all(self) -> None: ...
