"""Redis helpers: caching + security primitives.
Redis is required for refresh-token rotation in production; ordinary caching may fail open.
"""
import json

from app.logging_config import get_logger

logger = get_logger("cache")

try:
    import redis
    from app.config import settings

    _client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    _REDIS_AVAILABLE = True
except ImportError:
    _client = None
    _REDIS_AVAILABLE = False
    logger.info("مكتبة redis غير مثبّتة")


def cache_get(key: str):
    if not _REDIS_AVAILABLE or _client is None:
        return None
    try:
        value = _client.get(key)
        return json.loads(value) if value is not None else None
    except Exception:
        return None


def cache_set(key: str, value, ttl_seconds: int) -> None:
    if not _REDIS_AVAILABLE or _client is None:
        return
    try:
        _client.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception:
        logger.warning("تعذر الكتابة بـ Redis — تجاهل caching")


def cache_delete(key: str) -> None:
    if not _REDIS_AVAILABLE or _client is None:
        return
    try:
        _client.delete(key)
    except Exception:
        pass


def remember_refresh_token(jti: str, ttl_seconds: int) -> bool:
    """Store a refresh-token JTI. Fail closed because rotation depends on this."""
    if not _REDIS_AVAILABLE or _client is None:
        return False
    try:
        return bool(_client.set(f"refresh:jti:{jti}", "1", ex=max(1, ttl_seconds), nx=True))
    except Exception:
        logger.exception("Redis unavailable while storing refresh JTI")
        return False


def consume_refresh_token(jti: str) -> bool:
    """Atomically consume a refresh JTI to prevent replay after rotation."""
    if not _REDIS_AVAILABLE or _client is None:
        return False
    try:
        with _client.pipeline() as pipe:
            pipe.watch(f"refresh:jti:{jti}")
            if pipe.get(f"refresh:jti:{jti}") != "1":
                pipe.unwatch()
                return False
            pipe.multi()
            pipe.delete(f"refresh:jti:{jti}")
            pipe.execute()
            return True
    except Exception:
        return False
