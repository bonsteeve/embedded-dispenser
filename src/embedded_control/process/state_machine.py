"""Operator-gated transfer state machine with timeout management."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .config import ProcessConfig


class ProcessState(Enum):
    """Lifecycle states for a gated transfer operation."""

    IDLE = "idle"
    WAITING_OPERATOR = "waiting_operator"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"
    ABORTED = "aborted"


@dataclass
class ProcessRequest:
    """Request to start a gated transfer."""

    request_id: str
    target_quantity: float
    target_slot: str
    timestamp: float | None = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class ProcessProgress:
    """Tracks progress for an in-flight transfer."""

    request_id: str
    target_quantity: float
    completed_quantity: float = 0.0
    start_time: float | None = None
    pause_count: int = 0
    total_pause_duration: float = 0.0
    last_pause_time: float | None = None
    sample_count: int = 0
    throughput_rate: float = 0.0

    def __post_init__(self) -> None:
        if self.start_time is None:
            self.start_time = time.time()

    @property
    def percentage_complete(self) -> float:
        if self.target_quantity == 0:
            return 0.0
        return min(100.0, (self.completed_quantity / self.target_quantity) * 100)

    @property
    def elapsed_time(self) -> float:
        if self.start_time is None:
            return 0.0
        return (time.time() - self.start_time) - self.total_pause_duration


StateChangeCallback = Callable[
    [ProcessState, ProcessState, ProcessRequest | None], Awaitable[None] | None
]


class GatedTransferStateMachine:
    """
    State machine for operations that require operator confirmation.

    Typical flow:
      IDLE -> WAITING_OPERATOR -> ACTIVE <-> PAUSED -> COMPLETED

  The pattern applies to any process where an operator trigger gates
  start, pause, and resume — for example foot pedals, hold-to-run buttons,
  or safety interlocks on industrial equipment.
    """

    def __init__(
        self,
        config: ProcessConfig | None = None,
        on_state_change: StateChangeCallback | None = None,
    ) -> None:
        self.config = config or ProcessConfig()
        self.state = ProcessState.IDLE
        self.current_request: ProcessRequest | None = None
        self.progress: ProcessProgress | None = None
        self.on_state_change = on_state_change
        self._lock = asyncio.Lock()
        self._timeout_task: asyncio.Task[None] | None = None
        self.timeout_reason: str | None = None
        self.completion_reason: str | None = None
        self.abort_reason: str | None = None

    async def start(self, request: ProcessRequest) -> bool:
        """Begin a new transfer when the machine is idle."""
        async with self._lock:
            if self.state != ProcessState.IDLE:
                return False

            self.current_request = request
            self.progress = ProcessProgress(
                request_id=request.request_id,
                target_quantity=request.target_quantity,
            )
            await self._transition_to(ProcessState.WAITING_OPERATOR)
            self._start_timeout(
                self.config.operator_wait_timeout_seconds,
                ProcessState.TIMEOUT,
                "operator_wait",
            )
            return True

    async def on_operator_pressed(self) -> None:
        """Handle operator trigger press (start or resume)."""
        async with self._lock:
            if self.state == ProcessState.WAITING_OPERATOR:
                self._cancel_timeout()
                await self._transition_to(ProcessState.ACTIVE)
                self._start_timeout(
                    self.config.max_duration_seconds,
                    ProcessState.TIMEOUT,
                    "max_duration",
                )
            elif self.state == ProcessState.PAUSED and self.progress:
                if self.progress.last_pause_time is not None:
                    pause_duration = time.time() - self.progress.last_pause_time
                    self.progress.total_pause_duration += pause_duration
                    self.progress.last_pause_time = None
                self._cancel_timeout()
                await self._transition_to(ProcessState.ACTIVE)

    async def on_operator_released(self) -> None:
        """Handle operator trigger release (pause)."""
        async with self._lock:
            if self.state != ProcessState.ACTIVE:
                return
            if self.progress:
                self.progress.pause_count += 1
                self.progress.last_pause_time = time.time()
            await self._transition_to(ProcessState.PAUSED)
            self._start_timeout(
                self.config.pause_timeout_seconds,
                ProcessState.TIMEOUT,
                "operator_pause",
            )

    async def update_progress(self, completed_quantity: float) -> None:
        """Update completed quantity and finish when the target is reached."""
        async with self._lock:
            if self.progress is None:
                return
            self.progress.completed_quantity = completed_quantity
            if completed_quantity >= self.progress.target_quantity:
                self._cancel_timeout()
                self.completion_reason = "target_reached"
                await self._transition_to(ProcessState.COMPLETED)

    async def complete_early(self, throughput_rate: float, reason: str = "low_throughput") -> None:
        """Complete the operation before the target quantity is reached."""
        async with self._lock:
            if self.state != ProcessState.ACTIVE:
                return
            self._cancel_timeout()
            self.completion_reason = reason
            if self.progress:
                self.progress.throughput_rate = throughput_rate
            await self._transition_to(ProcessState.COMPLETED)

    async def error(self, error_message: str) -> None:
        """Transition to the error state."""
        async with self._lock:
            self._cancel_timeout()
            self.timeout_reason = error_message
            await self._transition_to(ProcessState.ERROR)

    async def abort(self, reason: str = "user_request") -> bool:
        """Abort an active operation."""
        async with self._lock:
            if self.state not in {
                ProcessState.WAITING_OPERATOR,
                ProcessState.ACTIVE,
                ProcessState.PAUSED,
            }:
                return False
            self._cancel_timeout()
            self.abort_reason = reason
            await self._transition_to(ProcessState.ABORTED)
            return True

    async def reset(self) -> None:
        """Return the machine to idle."""
        async with self._lock:
            self._cancel_timeout()
            self.current_request = None
            self.progress = None
            self.timeout_reason = None
            self.completion_reason = None
            self.abort_reason = None
            await self._transition_to(ProcessState.IDLE)

    async def _transition_to(self, new_state: ProcessState) -> None:
        old_state = self.state
        self.state = new_state
        if self.on_state_change is not None:
            result = self.on_state_change(old_state, new_state, self.current_request)
            if asyncio.iscoroutine(result):
                await result

    def _start_timeout(
        self,
        duration: int,
        timeout_state: ProcessState,
        reason: str | None = None,
    ) -> None:
        self._cancel_timeout()

        async def timeout_handler() -> None:
            await asyncio.sleep(duration)
            async with self._lock:
                self.timeout_reason = reason
                await self._transition_to(timeout_state)

        self._timeout_task = asyncio.create_task(timeout_handler())

    def _cancel_timeout(self) -> None:
        if self._timeout_task is not None and not self._timeout_task.done():
            self._timeout_task.cancel()
        self._timeout_task = None

    def get_status(self) -> dict[str, Any]:
        """Return a JSON-serializable status snapshot."""
        status: dict[str, Any] = {
            "state": self.state.value,
            "request_id": self.current_request.request_id if self.current_request else None,
        }
        if self.progress:
            status.update(
                {
                    "target_quantity": self.progress.target_quantity,
                    "completed_quantity": self.progress.completed_quantity,
                    "percentage_complete": round(self.progress.percentage_complete, 1),
                    "pause_count": self.progress.pause_count,
                    "elapsed_seconds": round(self.progress.elapsed_time, 1),
                    "sample_count": self.progress.sample_count,
                    "throughput_rate": round(self.progress.throughput_rate, 2),
                }
            )
        return status
