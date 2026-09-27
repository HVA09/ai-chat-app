from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChatResponse:
    conversation_id: int
    reply: str
    model: str

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "ChatResponse":
        return cls(
            conversation_id=int(payload["conversation_id"]),
            reply=str(payload["reply"]),
            model=str(payload["model"]),
        )
