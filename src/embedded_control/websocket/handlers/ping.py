"""Heartbeat handler for connection health checks."""

from typing import Any

from ..base import HandlerResponse, MessageHandler, ResponseType


class PingHandler(MessageHandler):
    """Responds to plain-text ping messages with pong."""

    DEFAULT_PRIORITY = 5

    def __init__(self, priority: int | None = None) -> None:
        super().__init__(priority if priority is not None else self.DEFAULT_PRIORITY)

    def can_handle(self, message: str, parsed_data: dict[str, Any] | None = None) -> bool:
        return message.strip().lower() == "ping"

    async def handle(
        self, message: str, parsed_data: dict[str, Any] | None = None
    ) -> HandlerResponse:
        return HandlerResponse(type=ResponseType.PLAIN_TEXT, data="pong")
