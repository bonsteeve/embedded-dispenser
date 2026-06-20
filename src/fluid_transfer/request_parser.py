"""Request parser for fluid transfer commands."""

import json
from typing import Any

from .config import FluidTransferConfig


class TransferRequestParser:
    """Validates JSON transfer requests."""

    def __init__(self, config: FluidTransferConfig | None = None) -> None:
        self.config = config or FluidTransferConfig()

    def parse(self, message: str) -> dict[str, Any]:
        try:
            data = json.loads(message)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError("Request must be a JSON object")

        for field in ("action", "volume", "request_id", "slot"):
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        if data["action"] != "transfer":
            raise ValueError(f"Invalid action: {data['action']}")

        volume = data["volume"]
        if not isinstance(volume, (int, float)) or volume <= 0:
            raise ValueError("volume must be a positive number")
        if volume < self.config.min_volume:
            raise ValueError(f"volume must be at least {self.config.min_volume}")
        if volume > self.config.max_volume:
            raise ValueError(f"volume cannot exceed {self.config.max_volume}")

        request_id = data["request_id"]
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("request_id must be a non-empty string")

        slot = data["slot"]
        if slot not in self.config.valid_slots:
            raise ValueError(f"Invalid slot: {slot}")

        return {
            "action": "transfer",
            "volume": float(volume),
            "request_id": request_id,
            "slot": slot,
        }
