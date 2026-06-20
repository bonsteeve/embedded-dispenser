"""Data types for S-curve acceleration profiles."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class SCurveParameters:
    """Parameters that define an S-curve acceleration envelope."""

    acceleration_time: float
    deceleration_time: float
    jerk_time_ratio: float = 0.3


@dataclass
class MovementPhase:
    """A single phase within a movement profile."""

    duration: float
    start_frequency: float
    end_frequency: float
    frequency_function: Callable[[float], float]


@dataclass
class AccelerationProfile:
    """Complete acceleration profile for a movement."""

    phases: list[MovementPhase]
    total_duration: float
    max_frequency: float
    total_steps: int
