"""Coordinates routing, response delivery, and optional broadcast."""

import json
from typing import Protocol

from .base import HandlerResponse, MessageHandler, ResponseType
from .handlers import EchoHandler, HealthHandler, PingHandler
from .router import MessageRouter


class WebSocketLike(Protocol):
    """Minimal WebSocket interface used by the processor."""

    async def send_text(self, data: str) -> None: ...


class ConnectionManager(Protocol):
    """Optional broadcast interface for multi-client scenarios."""

    async def broadcast(self, message: str, exclude: WebSocketLike | None = None) -> None: ...


class MessageProcessor:
    """Processes incoming WebSocket messages using registered handlers."""

    def __init__(self, handlers: list[MessageHandler] | None = None) -> None:
        self.router = MessageRouter()
        if handlers is not None:
            for handler in handlers:
                self.router.register_handler(handler)
        else:
            self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        self.router.register_handler(PingHandler())
        self.router.register_handler(HealthHandler())
        self.router.register_handler(EchoHandler())

    async def process(
        self,
        message: str,
        websocket: WebSocketLike,
        connection_manager: ConnectionManager | None = None,
    ) -> None:
        """Route a message and send the resulting response."""
        response = await self.router.route(message)
        if response is None:
            await websocket.send_text(f"Echo: {message}")
            return
        await self._send_response(response, websocket, connection_manager)

    async def _send_response(
        self,
        response: HandlerResponse,
        websocket: WebSocketLike,
        connection_manager: ConnectionManager | None,
    ) -> None:
        if response.type == ResponseType.PLAIN_TEXT:
            payload = response.data
        else:
            payload = json.dumps(response.data)

        await websocket.send_text(payload)

        if response.broadcast and connection_manager is not None:
            if response.type == ResponseType.PLAIN_TEXT:
                broadcast_message = f"Client sent: {str(response.data).replace('Echo: ', '')}"
            else:
                broadcast_message = f"Client sent: {json.dumps(response.data)}"

            if response.broadcast_exclude_sender:
                await connection_manager.broadcast(broadcast_message, exclude=websocket)
            else:
                await connection_manager.broadcast(broadcast_message)

    def add_handler(self, handler: MessageHandler) -> None:
        """Register an additional handler."""
        self.router.register_handler(handler)

    def remove_handler(self, handler: MessageHandler) -> None:
        """Unregister a handler."""
        self.router.unregister_handler(handler)
