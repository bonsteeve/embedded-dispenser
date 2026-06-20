"""Fallback handler for unrecognized messages."""

from typing import Any

from ..base import HandlerResponse, MessageHandler, ResponseType


class EchoHandler(MessageHandler):
    """Echoes unrecognized messages and optionally broadcasts them."""

    DEFAULT_PRIORITY = 1000

    def __init__(self, priority: int | None = None) -> None:
        super().__init__(priority if priority is not None else self.DEFAULT_PRIORITY)

    def can_handle(self, message: str, parsed_data: dict[str, Any] | None = None) -> bool:
        return True

    async def handle(
        self, message: str, parsed_data: dict[str, Any] | None = None
    ) -> HandlerResponse:
        return HandlerResponse(
            type=ResponseType.PLAIN_TEXT,
            data=f"Echo: {message}",
            broadcast=True,
            broadcast_exclude_sender=True,
        )
