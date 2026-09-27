from __future__ import annotations


class AIChatError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        request_id: str | None = None,
        retry_after: str | None = None,
        response: object | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        self.retry_after = retry_after
        self.response = response


class AuthenticationError(AIChatError):
    """Raised when the Developer API rejects the API key."""


class RateLimitError(AIChatError):
    """Raised when the Developer API rate limit is exceeded."""


class ValidationError(AIChatError):
    """Raised when the API rejects the request payload."""


class APIError(AIChatError):
    """Raised for other non-successful API responses."""
