"""Tests for the WebSocket routing layer."""

import json

import pytest

from embedded_control.websocket import MessageRouter, ResponseType
from embedded_control.websocket.handlers import EchoHandler, HealthHandler, PingHandler


@pytest.mark.asyncio
async def test_ping_handler_returns_pong() -> None:
    handler = PingHandler()
    assert handler.can_handle("ping", None)
    assert handler.can_handle(" PING ", None)
    assert not handler.can_handle("hello", None)

    response = await handler.handle("ping", None)
    assert response.type == ResponseType.PLAIN_TEXT
    assert response.data == "pong"


@pytest.mark.asyncio
async def test_health_handler_returns_status() -> None:
    handler = HealthHandler(service_name="demo")
    payload = json.dumps({"action": "health"})
    assert handler.can_handle(payload, json.loads(payload))

    response = await handler.handle(payload, json.loads(payload))
    assert response.type == ResponseType.STATUS
    assert response.data["status"] == "ok"
    assert response.data["service"] == "demo"


@pytest.mark.asyncio
async def test_router_respects_priority() -> None:
    router = MessageRouter()
    router.register_handler(EchoHandler())
    router.register_handler(PingHandler())

    response = await router.route("ping")
    assert response is not None
    assert response.data == "pong"


@pytest.mark.asyncio
async def test_echo_handler_is_fallback() -> None:
    router = MessageRouter()
    router.register_handler(PingHandler())
    router.register_handler(EchoHandler())

    response = await router.route("custom-message")
    assert response is not None
    assert "Echo: custom-message" in response.data
