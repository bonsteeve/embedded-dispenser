"""Message router for dispatching WebSocket messages to handlers."""

import json
from typing import Any

from .base import HandlerResponse, MessageHandler, ResponseType


class MessageRouter:
    """Routes messages to registered handlers in priority order."""

    def __init__(self) -> None:
        self._handlers: list[MessageHandler] = []

    def register_handler(self, handler: MessageHandler) -> None:
        """Register a handler and re-sort by priority."""
        self._handlers.append(handler)
        self._handlers.sort(key=lambda handler: handler.priority)

    def unregister_handler(self, handler: MessageHandler) -> None:
        """Remove a handler from the router."""
        if handler in self._handlers:
            self._handlers.remove(handler)

    def clear_handlers(self) -> None:
        """Remove all registered handlers."""
        self._handlers.clear()

    async def route(self, message: str) -> HandlerResponse | None:
        """
        Route a message to the first capable handler.

        Returns:
            The handler response, or None when no handler matches.
        """
        parsed_data: dict[str, Any] | None = None
        try:
            parsed_data = json.loads(message)
        except json.JSONDecodeError:
            pass

        for handler in self._handlers:
            if not handler.can_handle(message, parsed_data):
                continue

            error = handler.validate(message, parsed_data)
            if error:
                return HandlerResponse(
                    type=ResponseType.ERROR,
                    data={"type": "error", "error": error},
                )

            try:
                return await handler.handle(message, parsed_data)
            except Exception as exc:
                return HandlerResponse(
                    type=ResponseType.ERROR,
                    data={"type": "error", "error": f"Handler error: {exc}"},
                )

        return None

    @property
    def handlers(self) -> list[MessageHandler]:
        """Return a copy of the registered handler list."""
        return self._handlers.copy()
