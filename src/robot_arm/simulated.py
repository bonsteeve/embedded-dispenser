"""Software-only position feedback and motor drivers."""

import asyncio

from .interfaces import AxisPosition


class SimulatedPositionFeedback:
    """In-memory position tracker."""

    def __init__(self, horizontal: float = 0.0, vertical: float = 0.0) -> None:
        self._position = AxisPosition(horizontal=horizontal, vertical=vertical)

    def read_position(self) -> AxisPosition:
        return AxisPosition(
            horizontal=self._position.horizontal,
            vertical=self._position.vertical,
        )

    def set_position(self, horizontal: float, vertical: float) -> None:
        self._position = AxisPosition(horizontal=horizontal, vertical=vertical)


class SimulatedMotorDriver:
    """Motor driver that moves simulated position toward targets."""

    def __init__(
        self,
        feedback: SimulatedPositionFeedback,
        step_size: float = 10.0,
        move_delay: float = 0.01,
    ) -> None:
        self.feedback = feedback
        self.step_size = step_size
        self.move_delay = move_delay
        self._stopped = False

    async def move_vertical(self, target: float, speed: float) -> bool:
        self._stopped = False
        while not self._stopped:
            current = self.feedback.read_position().vertical
            if abs(current - target) <= self.step_size:
                pos = self.feedback.read_position()
                self.feedback.set_position(pos.horizontal, target)
                return True
            direction = 1 if target > current else -1
            pos = self.feedback.read_position()
            self.feedback.set_position(
                pos.horizontal,
                current + direction * self.step_size * speed,
            )
            await asyncio.sleep(self.move_delay)
        return False

    async def move_horizontal(self, target: float, speed: float) -> bool:
        self._stopped = False
        while not self._stopped:
            current = self.feedback.read_position().horizontal
            if abs(current - target) <= self.step_size:
                pos = self.feedback.read_position()
                self.feedback.set_position(target, pos.vertical)
                return True
            direction = 1 if target > current else -1
            pos = self.feedback.read_position()
            self.feedback.set_position(
                current + direction * self.step_size * speed,
                pos.vertical,
            )
            await asyncio.sleep(self.move_delay)
        return False

    async def stop_all(self) -> None:
        self._stopped = True
