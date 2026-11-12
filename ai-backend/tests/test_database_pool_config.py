"""Regression tests for bounded database connection pooling."""

import pytest
from pydantic import ValidationError

from app.config import Settings, settings
from app.database import commit_and_release_connection, engine


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


def test_commit_and_release_connection_preserves_loaded_scalars_and_session_setting():
    """A release boundary returns the only checkout without expiring loaded ORM data."""
    from sqlalchemy import Column, Integer, String, create_engine
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy.pool import QueuePool

    test_engine = create_engine(
        "sqlite://",
        poolclass=QueuePool,
        pool_size=1,
        max_overflow=0,
    )
    test_base = declarative_base()

    class PoolProbe(test_base):
        __tablename__ = "pool_release_probe"
        id = Column(Integer, primary_key=True)
        value = Column(String, nullable=False)

    test_base.metadata.create_all(test_engine)
    TestSession = sessionmaker(bind=test_engine, expire_on_commit=True)
    db = TestSession()
    try:
        db.add(PoolProbe(value="loaded before provider wait"))
        db.commit()
        probe = db.query(PoolProbe).one()
        assert test_engine.pool.checkedout() == 1
        assert db.expire_on_commit is True

        commit_and_release_connection(db)

        assert test_engine.pool.checkedout() == 0
        assert db.expire_on_commit is True
        assert probe.value == "loaded before provider wait"
        assert test_engine.pool.checkedout() == 0
    finally:
        db.close()
        test_engine.dispose()
