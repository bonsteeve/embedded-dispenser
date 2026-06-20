"""Configuration for gated transfer process state machines."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessConfig:
    """Timeout and limit settings for a gated transfer operation."""

    operator_wait_timeout_seconds: int = 30
    pause_timeout_seconds: int = 30
    max_duration_seconds: int = 120

    @classmethod
    def for_testing(cls) -> "ProcessConfig":
        """Return short timeouts suitable for unit tests."""
        return cls(
            operator_wait_timeout_seconds=1,
            pause_timeout_seconds=1,
            max_duration_seconds=2,
        )
