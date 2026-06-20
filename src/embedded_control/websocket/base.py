"""Base classes for WebSocket message handlers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ResponseType(Enum):
    """Categories of responses handlers may return."""

    SUCCESS = "success"
    ERROR = "error"
    ACKNOWLEDGMENT = "acknowledgment"
    STATUS = "status"
    PROGRESS = "progress"
    ECHO = "echo"
    PLAIN_TEXT = "plain_text"


@dataclass
class HandlerResponse:
    """Structured response from a message handler."""

    type: ResponseType
    data: Any
    broadcast: bool = False
    broadcast_exclude_sender: bool = True

    def to_json(self) -> dict[str, Any]:
        """Convert the response to a JSON-serializable dictionary."""
        if self.type == ResponseType.PLAIN_TEXT:
            return {"plain_text": self.data}
        return self.data


class MessageHandler(ABC):
    """Abstract base class for WebSocket message handlers."""

    def __init__(self, priority: int = 100) -> None:
        """
        Initialize the handler.

        Args:
            priority: Routing priority. Lower values are evaluated first.
        """
        self.priority = priority

    @abstractmethod
    def can_handle(self, message: str, parsed_data: dict[str, Any] | None = None) -> bool:
        """Return True when this handler should process the message."""

    @abstractmethod
    async def handle(
        self, message: str, parsed_data: dict[str, Any] | None = None
    ) -> HandlerResponse:
        """Process the message and return a response."""

    def validate(self, message: str, parsed_data: dict[str, Any] | None = None) -> str | None:
        """
        Optional validation hook.

        Returns:
            An error message when validation fails, otherwise None.
        """
        return None
