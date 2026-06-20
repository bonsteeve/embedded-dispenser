"""Configuration for fluid transfer operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FluidTransferConfig:
    """Settings for pumps, flow sensing, gates, and transfer limits."""

    min_volume: float = 1.0
    max_volume: float = 2000.0
    pump_default_speed: float = 50.0
    pump_min_speed: float = 10.0
    pump_max_speed: float = 100.0
    gate_close_delay_seconds: float = 0.3
    pulses_per_liter: int = 1000
    flow_update_interval_seconds: float = 0.5
    min_flow_rate_lpm: float = 0.5
    low_flow_timeout_seconds: float = 2.0
    operator_wait_timeout_seconds: int = 30
    pause_timeout_seconds: int = 30
    max_duration_seconds: int = 120
    valid_slots: frozenset[str] = frozenset({"A1", "A2", "A3", "B1", "B2", "B3"})

    @classmethod
    def for_testing(cls) -> "FluidTransferConfig":
        return cls(
            operator_wait_timeout_seconds=1,
            pause_timeout_seconds=1,
            max_duration_seconds=2,
            gate_close_delay_seconds=0.05,
            low_flow_timeout_seconds=0.5,
        )

    def to_process_config(self):
        """Convert to the core framework process configuration."""
        from embedded_control.process import ProcessConfig

        return ProcessConfig(
            operator_wait_timeout_seconds=self.operator_wait_timeout_seconds,
            pause_timeout_seconds=self.pause_timeout_seconds,
            max_duration_seconds=self.max_duration_seconds,
        )
