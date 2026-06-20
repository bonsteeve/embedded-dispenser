"""Closed-loop positioning retry with tolerance checking."""

import logging

from .config import RobotArmConfig
from .interfaces import AxisPosition, MotionTarget, MotorDriver, PositionFeedback


class PositioningRetryHandler:
    """
    Applies corrective moves when axis position is outside tolerance.

    This is a simplified version of the production retry subsystem,
    demonstrating the Protocol-based design without hardware coupling.
    """

    def __init__(
        self,
        feedback: PositionFeedback,
        motor: MotorDriver,
        config: RobotArmConfig | None = None,
    ) -> None:
        self.feedback = feedback
        self.motor = motor
        self.config = config or RobotArmConfig()
        self.logger = logging.getLogger(__name__)

    def is_within_tolerance(self, position: AxisPosition, target: MotionTarget) -> bool:
        h_ok = abs(position.horizontal - target.horizontal) <= self.config.horizontal_tolerance
        v_ok = abs(position.vertical - target.vertical) <= self.config.vertical_tolerance
        return h_ok and v_ok

    async def move_to_target(self, target: MotionTarget) -> tuple[bool, int]:
        """
        Move to target with retry correction.

        Returns:
            Tuple of (success, retry_attempts).
        """
        attempts = 0
        while attempts <= self.config.max_retry_attempts:
            await self.motor.move_vertical(target.vertical, self.config.default_speed)
            await self.motor.move_horizontal(target.horizontal, self.config.default_speed)

            position = self.feedback.read_position()
            if self.is_within_tolerance(position, target):
                return True, attempts

            attempts += 1
            self.logger.debug(
                "Position correction attempt %d: h=%.1f v=%.1f",
                attempts,
                position.horizontal,
                position.vertical,
            )

        return False, attempts
