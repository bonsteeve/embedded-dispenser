"""Pure mathematical functions for S-curve profile generation."""

import math
from collections.abc import Callable


class SCurveFunctions:
    """Stateless S-curve mathematics with no hardware dependencies."""

    @staticmethod
    def create_jerk_up_function(
        start_freq: float, end_freq: float, duration: float
    ) -> Callable[[float], float]:
        def jerk_up(t: float) -> float:
            if t <= 0:
                return start_freq
            if t >= duration:
                return end_freq
            progress = t / duration
            smooth_progress = 0.5 * (1 - math.cos(math.pi * progress))
            return start_freq + (end_freq - start_freq) * smooth_progress

        return jerk_up

    @staticmethod
    def create_jerk_down_function(
        start_freq: float, end_freq: float, duration: float
    ) -> Callable[[float], float]:
        def jerk_down(t: float) -> float:
            if t <= 0:
                return start_freq
            if t >= duration:
                return end_freq
            progress = t / duration
            smooth_progress = 0.5 * (1 + math.cos(math.pi * (1 - progress)))
            return start_freq + (end_freq - start_freq) * smooth_progress

        return jerk_down

    @staticmethod
    def create_linear_function(
        start_freq: float, end_freq: float, duration: float
    ) -> Callable[[float], float]:
        def linear(t: float) -> float:
            if t <= 0:
                return start_freq
            if t >= duration:
                return end_freq
            progress = t / duration
            return start_freq + (end_freq - start_freq) * progress

        return linear

    @staticmethod
    def create_constant_function(frequency: float) -> Callable[[float], float]:
        return lambda _t: frequency

    @staticmethod
    def calculate_phase_durations(
        acceleration_time: float, deceleration_time: float, jerk_ratio: float = 0.3
    ) -> tuple[float, float, float, float]:
        accel_jerk_time = max(acceleration_time * jerk_ratio, 0.1)
        accel_constant_time = max(acceleration_time * (1 - 2 * jerk_ratio), 0.1)
        decel_jerk_time = max(deceleration_time * jerk_ratio, 0.1)
        decel_constant_time = max(deceleration_time * (1 - 2 * jerk_ratio), 0.1)
        return accel_jerk_time, accel_constant_time, decel_jerk_time, decel_constant_time

    @staticmethod
    def estimate_steps_in_phases(phases: list) -> int:
        total_steps = 0.0
        for phase in phases:
            avg_frequency = (phase.start_frequency + phase.end_frequency) / 2
            total_steps += avg_frequency * phase.duration
        return int(total_steps)
