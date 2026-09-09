"""Redis helpers: caching + security primitives.
Redis is required for refresh-token rotation and one-time auth tokens in production.
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


def _safe(fn, default=None):
    if not _REDIS_AVAILABLE or _client is None:
        return default
    try:
        return fn()
    except Exception:
        return default


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


def _remember_once(prefix: str, jti: str, ttl_seconds: int) -> bool:
    if not _REDIS_AVAILABLE or _client is None:
        return False
    try:
        return bool(_client.set(f"{prefix}:{jti}", "1", ex=max(1, ttl_seconds), nx=True))
    except Exception:
        logger.exception("Redis unavailable while storing one-time token")
        return False


def _consume_once(prefix: str, jti: str) -> bool:
    """Atomically consume a one-time token using a Redis server-side script."""
    if not _REDIS_AVAILABLE or _client is None:
        return False
    key = f"{prefix}:{jti}"
    script = """
    if redis.call('GET', KEYS[1]) == '1' then
        redis.call('DEL', KEYS[1])
        return 1
    end
    return 0
    """
    try:
        return bool(_client.eval(script, 1, key))
    except Exception:
        logger.exception("Redis unavailable while consuming one-time token")
        return False


def remember_refresh_token(jti: str, ttl_seconds: int) -> bool:
    """Store a refresh-token JTI. Fail closed because rotation depends on this."""
    return _remember_once("refresh:jti", jti, ttl_seconds)


def consume_refresh_token(jti: str) -> bool:
    """Atomically consume a refresh JTI to prevent replay after rotation."""
    return _consume_once("refresh:jti", jti)


def remember_email_verification_token(jti: str, ttl_seconds: int) -> bool:
    """Store an email-verification JTI so the verification link can be used once."""
    return _remember_once("email_verify:jti", jti, ttl_seconds)


def consume_email_verification_token(jti: str) -> bool:
    """Atomically consume an email-verification JTI."""
    return _consume_once("email_verify:jti", jti)


def remember_password_reset_token(jti: str, ttl_seconds: int) -> bool:
    """Store a password-reset JTI so the reset link can be used once."""
    return _remember_once("password_reset:jti", jti, ttl_seconds)


def consume_password_reset_token(jti: str) -> bool:
    """Atomically consume a password-reset JTI."""
    return _consume_once("password_reset:jti", jti)
