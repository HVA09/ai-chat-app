from __future__ import annotations

from typing import Any

import httpx

from .errors import (
    AIChatError,
    APIError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
)
from .models import ChatResponse


API_VERSION = "v1"
DEFAULT_BASE_URL = "https://api.example.com/v1"


class AIChatClient:
    """Small synchronous client for the AI Chat SaaS Developer API v1."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("api_key is required")
        if timeout <= 0:
            raise ValueError("timeout must be greater than 0")

        normalized = base_url.rstrip("/")
        if not normalized.endswith(f"/{API_VERSION}"):
            raise ValueError(
                f"base_url must point to the Developer API {API_VERSION} namespace"
            )

        self.api_key = api_key.strip()
        self.base_url = normalized
        self.timeout = timeout
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "AIChatClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def chat(
        self,
        message: str,
        *,
        conversation_id: int | None = None,
        workspace_id: int | None = None,
        assistant_id: int | None = None,
        model: str | None = None,
    ) -> ChatResponse:
        if not message or not message.strip():
            raise ValueError("message is required")

        payload: dict[str, Any] = {"message": message.strip()}
        optional = {
            "conversation_id": conversation_id,
            "workspace_id": workspace_id,
            "assistant_id": assistant_id,
            "model": model.strip() if isinstance(model, str) and model.strip() else None,
        }
        payload.update({key: value for key, value in optional.items() if value is not None})

        response = self._client.post(
            f"{self.base_url}/chat",
            headers={
                "X-API-Key": self.api_key,
                "Accept": "application/json",
                "User-Agent": "ai-chat-saas-python/0.1.0",
            },
            json=payload,
        )
        return self._decode_chat_response(response)

    def _decode_chat_response(self, response: httpx.Response) -> ChatResponse:
        request_id = response.headers.get("X-Request-ID")
        retry_after = response.headers.get("Retry-After")

        if 200 <= response.status_code < 300:
            try:
                return ChatResponse.from_json(response.json())
            except (ValueError, KeyError, TypeError) as exc:
                raise APIError(
                    "Developer API returned an invalid response payload.",
                    status_code=response.status_code,
                    request_id=request_id,
                    response=response,
                ) from exc

        detail = self._error_message(response)
        error_type = {
            401: AuthenticationError,
            422: ValidationError,
            429: RateLimitError,
        }.get(response.status_code, APIError)
        raise error_type(
            detail,
            status_code=response.status_code,
            request_id=request_id,
            retry_after=retry_after,
            response=response,
        )

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text.strip() or f"Developer API error ({response.status_code})."

        if isinstance(payload, dict):
            detail = payload.get("detail")
            if detail:
                return str(detail)
            message = payload.get("message")
            if message:
                return str(message)
        return f"Developer API error ({response.status_code})."
