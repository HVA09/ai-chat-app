"""
Middleware خفيف:
- X-Request-ID لتتبع الطلبات وربط الطلب بسجلات الخادم
- Rate limit لمسارات المصادقة الحساسة باستخدام Redis في التشغيل الحقيقي
- حد عام للطلبات عبر Redis ليبقى فعالًا حتى مع أكثر من replica
"""
from __future__ import annotations

import ipaddress
import re
import time
import uuid
from collections import defaultdict, deque

from app.logging_config import get_logger, get_request_id, reset_request_id, set_request_id
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# مسار → (حد الطلبات، نافذة بالثواني)
_AUTH_LIMITS: dict[str, tuple[int, int]] = {
    "/auth/login": (10, 60),
    "/auth/register": (5, 60),
    "/auth/password-reset/request": (5, 60),
    "/auth/verify-email/request": (5, 60),
    "/auth/2fa/setup": (5, 60),
    "/auth/2fa/enable": (10, 60),
    "/auth/2fa/disable": (10, 60),
}

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_GENERAL_RATE_LIMIT = (60, 60)

# Fallback only for non-production environments when Redis is unavailable.
_hits: dict[str, dict[str, deque[float]]] = defaultdict(lambda: defaultdict(deque))

http_logger = get_logger("http")


def _client_ip(request: Request) -> str:
    """Trust X-Forwarded-For only when the immediate peer is in a trusted proxy network."""
    peer = request.client.host if request.client else None
    try:
        from app.config import settings

        trusted = (
            any(
                ipaddress.ip_address(peer) in ipaddress.ip_network(net)
                for net in settings.TRUSTED_PROXY_NETWORKS
            )
            if peer
            else False
        )
    except (ValueError, TypeError):
        trusted = False
    if trusted:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            candidate = forwarded.split(",")[0].strip()
            try:
                ipaddress.ip_address(candidate)
                return candidate
            except ValueError:
                pass
    return peer or "unknown"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        incoming_request_id = request.headers.get("x-request-id")
        request_id = (
            incoming_request_id
            if incoming_request_id and _REQUEST_ID_RE.fullmatch(incoming_request_id)
            else uuid.uuid4().hex[:16]
        )

        request.state.request_id = request_id
        context_token = set_request_id(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            reset_request_id(context_token)


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """Log request outcome and latency without recording query strings or secrets."""

    async def dispatch(self, request: Request, call_next) -> Response:
        started_at = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        except Exception:
            http_logger.exception(
                "HTTP %s %s unhandled_exception latency_ms=%s request_id=%s",
                request.method,
                request.url.path,
                round((time.perf_counter() - started_at) * 1000),
                request.scope.get("request_id", get_request_id()),
            )
            raise
        finally:
            if response is not None:
                latency_ms = round((time.perf_counter() - started_at) * 1000)
                log_level = 30 if response.status_code >= 400 else 20
                request_id = request.scope.get(
                    "request_id", getattr(request.state, "request_id", get_request_id())
                )
                http_logger.log(
                    log_level,
                    "HTTP %s %s %s latency_ms=%s request_id=%s",
                    request.method,
                    request.url.path,
                    response.status_code,
                    latency_ms,
                    request_id,
                )


def _in_memory_rate_limit(ip: str, path: str, max_hits: int, window: int) -> tuple[bool, int]:
    now = time.monotonic()
    bucket = _hits[ip][path]
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    if len(bucket) >= max_hits:
        return False, len(bucket)
    bucket.append(now)

    # منع نمو الذاكرة بلا حدود في حالة آلاف عناوين IP مختلفة.
    if len(_hits) > 10000:
        stale_ips = [
            key
            for key, paths in _hits.items()
            if all(not values or now - values[-1] > 300 for values in paths.values())
        ]
        for key in stale_ips[:5000]:
            _hits.pop(key, None)
    return True, len(bucket)


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # عطّل أثناء الاختبارات عشان ما تنهار مجموعة pytest من نفس الـ IP
        try:
            from app.config import settings

            if settings.ENVIRONMENT in ("test", "testing"):
                return await call_next(request)
        except Exception:
            settings = None

        path = request.url.path.rstrip("/") or "/"
        limit_cfg = _AUTH_LIMITS.get(path) or _AUTH_LIMITS.get(path + "/")
        if limit_cfg and request.method.upper() == "POST":
            max_hits, window = limit_cfg
            ip = _client_ip(request)

            from app.cache import check_rate_limit

            redis_result = check_rate_limit(f"auth:{ip}:{path}", max_hits, window)
            if redis_result is None:
                if settings is not None and settings.ENVIRONMENT == "production":
                    return JSONResponse(
                        status_code=503,
                        content={"detail": "خدمة تحديد المعدل غير متاحة مؤقتًا"},
                        headers={"Retry-After": "30"},
                    )
                allowed, current_count = _in_memory_rate_limit(ip, path, max_hits, window)
            else:
                allowed, current_count = redis_result

            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"محاولات كثيرة. حاول بعد قليل (حد {max_hits} كل {window} ثانية)"
                    },
                    headers={"Retry-After": str(window)},
                )

        return await call_next(request)


class GeneralRateLimitMiddleware(BaseHTTPMiddleware):
    """Apply a shared IP-based request limit in production via Redis."""

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            from app.config import settings

            if settings.ENVIRONMENT in ("test", "testing"):
                return await call_next(request)
        except Exception:
            settings = None

        # Health checks and CORS preflight must remain available even during bursts.
        if request.method.upper() == "OPTIONS" or request.url.path.rstrip("/") == "/health":
            return await call_next(request)

        max_hits, window = _GENERAL_RATE_LIMIT
        ip = _client_ip(request)

        from app.cache import check_rate_limit_with_reset

        redis_result = check_rate_limit_with_reset(f"global:{ip}", max_hits, window)
        if redis_result is None:
            # Auth endpoints fail closed above. For the broad limiter, preserve
            # application availability if Redis is temporarily unavailable.
            http_logger.warning("Redis unavailable for global rate limit; request allowed")
            return await call_next(request)

        allowed, current_count, reset_at = redis_result
        remaining = max(0, max_hits - current_count)
        headers = {
            "X-RateLimit-Limit": str(max_hits),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_at),
        }

        if not allowed:
            headers["Retry-After"] = str(max(1, reset_at - int(time.time())))
            return JSONResponse(
                status_code=429,
                content={"detail": "طلبات كثيرة. حاول مرة أخرى بعد قليل."},
                headers=headers,
            )

        response = await call_next(request)
        for key, value in headers.items():
            response.headers[key] = value
        return response
