"""S-curve motion profiling for stepper and pulse-driven actuators."""

from .calculator import AccelerationProfileCalculator
from .curve_functions import SCurveFunctions
from .profile_types import AccelerationProfile, MovementPhase, SCurveParameters

__all__ = [
    "AccelerationProfile",
    "AccelerationProfileCalculator",
    "MovementPhase",
    "SCurveFunctions",
    "SCurveParameters",
]
