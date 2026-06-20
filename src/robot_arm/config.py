"""Configuration for robot arm motion."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RobotArmConfig:
    """Tolerances, speeds, and slot layout for motion planning."""

    horizontal_tolerance: float = 5.0
    vertical_tolerance: float = 5.0
    default_speed: float = 1.0
    max_retry_attempts: int = 3
    stage_delay_seconds: float = 0.01
    slots: dict[str, tuple[float, float, int]] = field(
        default_factory=lambda: {
            "A1": (100.0, 200.0, 1),
            "A2": (200.0, 200.0, 1),
            "A3": (300.0, 200.0, 1),
            "B1": (100.0, 400.0, 2),
            "B2": (200.0, 400.0, 2),
            "B3": (300.0, 400.0, 2),
        }
    )

    @classmethod
    def for_testing(cls) -> "RobotArmConfig":
        return cls(stage_delay_seconds=0.001, max_retry_attempts=2)
