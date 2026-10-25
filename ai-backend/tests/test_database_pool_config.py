"""Regression tests for bounded database connection pooling."""

import pytest
from pydantic import ValidationError

from app.config import Settings, settings
from app.database import engine


def test_database_pool_defaults_are_bounded_for_session_poolers():
    """Each API/worker process must not open an oversized independent pool."""
    assert settings.DATABASE_POOL_SIZE == 2
    assert settings.DATABASE_MAX_OVERFLOW == 1
    assert settings.DATABASE_POOL_TIMEOUT_SECONDS == 15
    assert engine.pool.size() == settings.DATABASE_POOL_SIZE
    assert engine.pool._max_overflow == settings.DATABASE_MAX_OVERFLOW
    assert engine.pool._timeout == settings.DATABASE_POOL_TIMEOUT_SECONDS


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("DATABASE_POOL_SIZE", 0),
        ("DATABASE_MAX_OVERFLOW", -1),
        ("DATABASE_POOL_TIMEOUT_SECONDS", 0),
    ],
)
def test_database_pool_settings_reject_invalid_values(field, value):
    """Misconfigured environment overrides should fail during startup validation."""
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            DATABASE_URL="sqlite://",
            JWT_SECRET_KEY="test-secret",
            AI_API_KEY="test-provider-key",
            **{field: value},
        )
