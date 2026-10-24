"""Regression tests for bounded database connection pooling."""

from app.config import settings
from app.database import engine


def test_database_pool_defaults_are_bounded_for_session_poolers():
    """Each API/worker process must not open an oversized independent pool."""
    assert settings.DATABASE_POOL_SIZE == 2
    assert settings.DATABASE_MAX_OVERFLOW == 1
    assert settings.DATABASE_POOL_TIMEOUT_SECONDS == 15
    assert engine.pool.size() == settings.DATABASE_POOL_SIZE
    assert engine.pool._max_overflow == settings.DATABASE_MAX_OVERFLOW
    assert engine.pool._timeout == settings.DATABASE_POOL_TIMEOUT_SECONDS
