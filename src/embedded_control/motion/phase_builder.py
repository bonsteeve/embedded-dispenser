"""Constructs movement phases for S-curve acceleration profiles."""

from .curve_functions import SCurveFunctions
from .profile_types import MovementPhase


class MovementPhaseBuilder:
    """Builds acceleration, cruise, and deceleration phases."""

    def __init__(self, min_frequency: float, max_frequency: float) -> None:
        self.min_frequency = min_frequency
        self.max_frequency = max_frequency
        self.functions = SCurveFunctions()

    def build_acceleration_phases(
        self, jerk_time: float, constant_time: float, max_freq: float
    ) -> list[MovementPhase]:
        phases: list[MovementPhase] = []

        if jerk_time > 0:
            end_freq = self.min_frequency + (max_freq - self.min_frequency) * 0.3
            phases.append(
                MovementPhase(
                    duration=jerk_time,
                    start_frequency=self.min_frequency,
                    end_frequency=end_freq,
                    frequency_function=self.functions.create_jerk_up_function(
                        self.min_frequency, end_freq, jerk_time
                    ),
                )
            )

        if constant_time > 0:
            start_freq = phases[-1].end_frequency if phases else self.min_frequency
            end_freq = max_freq * 0.8
            phases.append(
                MovementPhase(
                    duration=constant_time,
                    start_frequency=start_freq,
                    end_frequency=end_freq,
                    frequency_function=self.functions.create_linear_function(
                        start_freq, end_freq, constant_time
                    ),
                )
            )

        if jerk_time > 0:
            start_freq = phases[-1].end_frequency if phases else self.min_frequency
            phases.append(
                MovementPhase(
                    duration=jerk_time,
                    start_frequency=start_freq,
                    end_frequency=max_freq,
                    frequency_function=self.functions.create_jerk_down_function(
                        start_freq, max_freq, jerk_time
                    ),
                )
            )

        return phases

    def build_deceleration_phases(
        self, jerk_time: float, constant_time: float, max_freq: float
    ) -> list[MovementPhase]:
        phases: list[MovementPhase] = []

        if jerk_time > 0:
            end_freq = max_freq * 0.8
            phases.append(
                MovementPhase(
                    duration=jerk_time,
                    start_frequency=max_freq,
                    end_frequency=end_freq,
                    frequency_function=self.functions.create_jerk_up_function(
                        max_freq, end_freq, jerk_time
                    ),
                )
            )

        if constant_time > 0:
            start_freq = phases[-1].end_frequency if phases else max_freq
            end_freq = self.min_frequency + (max_freq - self.min_frequency) * 0.3
            phases.append(
                MovementPhase(
                    duration=constant_time,
                    start_frequency=start_freq,
                    end_frequency=end_freq,
                    frequency_function=self.functions.create_linear_function(
                        start_freq, end_freq, constant_time
                    ),
                )
            )

        if jerk_time > 0:
            start_freq = phases[-1].end_frequency if phases else max_freq
            phases.append(
                MovementPhase(
                    duration=jerk_time,
                    start_frequency=start_freq,
                    end_frequency=self.min_frequency,
                    frequency_function=self.functions.create_jerk_down_function(
                        start_freq, self.min_frequency, jerk_time
                    ),
                )
            )

        return phases

    def build_constant_velocity_phase(self, max_freq: float, duration: float) -> MovementPhase:
        return MovementPhase(
            duration=duration,
            start_frequency=max_freq,
            end_frequency=max_freq,
            frequency_function=self.functions.create_constant_function(max_freq),
        )
