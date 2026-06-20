"""Structured health and status reporting handler."""

from typing import Any

from ..base import HandlerResponse, MessageHandler, ResponseType


class HealthHandler(MessageHandler):
    """Returns system health when clients send a health-check action."""

    DEFAULT_PRIORITY = 10

    def __init__(self, priority: int | None = None, service_name: str = "embedded-control") -> None:
        super().__init__(priority if priority is not None else self.DEFAULT_PRIORITY)
        self.service_name = service_name

    def can_handle(self, message: str, parsed_data: dict[str, Any] | None = None) -> bool:
        if parsed_data is None:
            return False
        return parsed_data.get("action") == "health"

    async def handle(
        self, message: str, parsed_data: dict[str, Any] | None = None
    ) -> HandlerResponse:
        return HandlerResponse(
            type=ResponseType.STATUS,
            data={
                "type": "health",
                "status": "ok",
                "service": self.service_name,
            },
        )
