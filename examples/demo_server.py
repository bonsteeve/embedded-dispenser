"""Runnable FastAPI WebSocket demo for the embedded control framework."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from embedded_control.websocket import MessageProcessor

app = FastAPI(
    title="Embedded Control Framework Demo",
    description="Demonstrates priority-based WebSocket message routing.",
    version="0.1.0",
)

processor = MessageProcessor()


class DemoConnectionManager:
    """Minimal in-memory connection manager for broadcast demos."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str, exclude: WebSocket | None = None) -> None:
        for connection in self.active_connections:
            if connection is exclude:
                continue
            await connection.send_text(message)


manager = DemoConnectionManager()


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "embedded-control-framework-demo",
        "websocket": "/ws",
        "health": "/health",
    }


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "connections": len(manager.active_connections)})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            await processor.process(message, websocket, manager)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("demo_server:app", host="0.0.0.0", port=8080, reload=True)
