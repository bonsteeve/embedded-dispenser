"""Tests for S-curve motion profiling."""

from embedded_control.motion import (
    AccelerationProfileCalculator,
    SCurveFunctions,
    SCurveParameters,
)


def test_jerk_function_is_smooth_at_boundaries() -> None:
    fn = SCurveFunctions.create_jerk_up_function(100.0, 1000.0, 1.0)

    assert fn(0.0) == 100.0
    assert fn(1.0) == 1000.0
    midpoint = fn(0.5)
    assert 100.0 < midpoint < 1000.0


def test_profile_has_phases_and_positive_duration() -> None:
    calculator = AccelerationProfileCalculator(min_frequency=100.0, max_frequency=5000.0)
    params = SCurveParameters(acceleration_time=0.5, deceleration_time=0.5)

    profile = calculator.calculate_s_curve_profile(params, target_frequency=3000.0, total_steps=500)

    assert profile.total_steps == 500
    assert profile.total_duration > 0
    assert len(profile.phases) >= 3
    assert profile.max_frequency == 3000.0


def test_frequency_lookup_within_profile() -> None:
    calculator = AccelerationProfileCalculator(min_frequency=100.0, max_frequency=5000.0)
    params = SCurveParameters(acceleration_time=0.4, deceleration_time=0.4)
    profile = calculator.calculate_s_curve_profile(params, target_frequency=2000.0, total_steps=200)

    start_freq = calculator.get_frequency_at_step_ratio(profile, 0.0)
    end_freq = calculator.get_frequency_at_step_ratio(profile, 1.0)

    assert start_freq >= 100.0
    assert end_freq >= 100.0
