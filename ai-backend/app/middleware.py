"""
Middleware خفيف:
- X-Request-ID لتتبع الطلبات
- Rate limit لمسارات المصادقة الحساسة
"""
from __future__ import annotations

import ipaddress
import time
import uuid
from collections import defaultdict, deque

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

# ip → path → timestamps
_hits: dict[str, dict[str, deque[float]]] = defaultdict(lambda: defaultdict(deque))


def _client_ip(request: Request) -> str:
    """Trust X-Forwarded-For only when the immediate peer is in a trusted proxy network."""
    peer = request.client.host if request.client else None
    try:
        from app.config import settings
        trusted = any(
            ipaddress.ip_address(peer) in ipaddress.ip_network(net)
            for net in settings.TRUSTED_PROXY_NETWORKS
        ) if peer else False
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
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # عطّل أثناء الاختبارات عشان ما تنهار مجموعة pytest من نفس الـ IP
        try:
            from app.config import settings
            if settings.ENVIRONMENT in ("test", "testing"):
                return await call_next(request)
        except Exception:
            pass

        path = request.url.path.rstrip("/") or "/"
        limit_cfg = _AUTH_LIMITS.get(path) or _AUTH_LIMITS.get(path + "/")
        if limit_cfg and request.method.upper() == "POST":
            max_hits, window = limit_cfg
            ip = _client_ip(request)
            now = time.monotonic()
            bucket = _hits[ip][path]
            while bucket and now - bucket[0] > window:
                bucket.popleft()
            if len(bucket) >= max_hits:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"محاولات كثيرة. حاول بعد قليل (حد {max_hits} كل {window} ثانية)"
                    },
                    headers={"Retry-After": str(window)},
                )
            bucket.append(now)

            # منع نمو الذاكرة بلا حدود في حالة آلاف عناوين IP مختلفة.
            if len(_hits) > 10000:
                stale_ips = [
                    key for key, paths in _hits.items()
                    if all(not values or now - values[-1] > 300 for values in paths.values())
                ]
                for key in stale_ips[:5000]:
                    _hits.pop(key, None)

        return await call_next(request)
