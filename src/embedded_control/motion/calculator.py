"""Orchestrates S-curve profile calculation."""

import logging

from .curve_functions import SCurveFunctions
from .phase_builder import MovementPhaseBuilder
from .profile_types import AccelerationProfile, SCurveParameters


class AccelerationProfileCalculator:
    """Coordinates math and phase construction to build movement profiles."""

    def __init__(self, min_frequency: float, max_frequency: float) -> None:
        self.min_frequency = min_frequency
        self.max_frequency = max_frequency
        self.logger = logging.getLogger(__name__)
        self.functions = SCurveFunctions()
        self.phase_builder = MovementPhaseBuilder(min_frequency, max_frequency)

    def calculate_s_curve_profile(
        self,
        params: SCurveParameters,
        target_frequency: float,
        total_steps: int,
    ) -> AccelerationProfile:
        target_frequency = max(self.min_frequency, min(target_frequency, self.max_frequency))

        accel_jerk_time, accel_constant_time, decel_jerk_time, decel_constant_time = (
            self.functions.calculate_phase_durations(
                params.acceleration_time,
                params.deceleration_time,
                params.jerk_time_ratio,
            )
        )

        phases = self.phase_builder.build_acceleration_phases(
            accel_jerk_time, accel_constant_time, target_frequency
        )

        accel_steps = self.functions.estimate_steps_in_phases(phases)
        decel_steps = accel_steps
        constant_steps = max(0, total_steps - accel_steps - decel_steps)
        constant_duration = constant_steps / target_frequency if target_frequency > 0 else 0.0

        if constant_duration > 0:
            phases.append(
                self.phase_builder.build_constant_velocity_phase(
                    target_frequency, constant_duration
                )
            )

        phases.extend(
            self.phase_builder.build_deceleration_phases(
                decel_jerk_time, decel_constant_time, target_frequency
            )
        )

        total_duration = sum(phase.duration for phase in phases)
        return AccelerationProfile(
            phases=phases,
            total_duration=total_duration,
            max_frequency=target_frequency,
            total_steps=total_steps,
        )

    def get_frequency_at_step_ratio(self, profile: AccelerationProfile, step_ratio: float) -> float:
        if step_ratio <= 0:
            return profile.phases[0].start_frequency if profile.phases else self.min_frequency
        if step_ratio >= 1.0:
            return profile.phases[-1].end_frequency if profile.phases else self.min_frequency

        elapsed_time = step_ratio * profile.total_duration
        current_time = 0.0

        for phase in profile.phases:
            if elapsed_time <= current_time + phase.duration:
                phase_time = elapsed_time - current_time
                return phase.frequency_function(phase_time)
            current_time += phase.duration

        return profile.phases[-1].end_frequency if profile.phases else self.min_frequency
