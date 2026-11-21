"""Tests for immutable storage-profile identity capture."""
import os
from unittest.mock import MagicMock

import pytest
from sqlalchemy.engine import make_url

from app.config import settings
from app.services import storage_profiles


def _require_isolated_local_test_database():
    """Skip concurrency writes unless pytest targets the disposable local CI DB."""
    value = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/ai_backend_test",
    )
    parsed = make_url(value)
    if (
        parsed.drivername.split("+", 1)[0] != "postgresql"
        or parsed.host not in {"localhost", "127.0.0.1"}
        or parsed.port != 5432
        or parsed.database != "ai_backend_test"
        or parsed.query
    ):
        pytest.skip(
            "Concurrent storage-profile test requires the isolated "
            "localhost:5432/ai_backend_test database"
        )


def test_safe_endpoint_preserves_path_and_port_without_credentials():
    assert storage_profiles._safe_endpoint(
        "https://objects.example.test:9443/s3/api/"
    ) == "https://objects.example.test:9443/s3/api"


@pytest.mark.parametrize(
    "value",
    [
        "file:///tmp/storage",
        "https://objects.example.test?token=secret",
        "https://objects.example.test#fragment",
        "https://objects.example.test:invalid",
        "https://user:password@objects.example.test",
    ],
)
def test_safe_endpoint_rejects_unsafe_or_ambiguous_urls(value):
    with pytest.raises(ValueError):
        storage_profiles._safe_endpoint(value)


def test_get_or_create_active_profile_uses_s3_identity_without_secret_values(monkeypatch):
    monkeypatch.setattr(settings, "S3_BUCKET", "private-bucket")
    monkeypatch.setattr(settings, "S3_ENDPOINT_URL", "https://objects.example.test/s3")
    monkeypatch.setattr(settings, "S3_REGION", "us-east-1")
    monkeypatch.setattr(settings, "S3_ACCESS_KEY_ID", "do-not-persist-access")
    monkeypatch.setattr(settings, "S3_SECRET_ACCESS_KEY", "do-not-persist-secret")
    monkeypatch.setattr(storage_profiles, "_s3_enabled", lambda: True)
    db = MagicMock()
    profile = MagicMock()
    db.get.return_value = profile

    assert storage_profiles.get_or_create_active_storage_profile(db) is profile
    params = db.execute.call_args.args[0].compile().params
    assert params["provider"] == "s3"
    assert params["bucket"] == "private-bucket"
    assert params["endpoint_url"] == "https://objects.example.test/s3"
    assert "do-not-persist-access" not in repr(params)
    assert "do-not-persist-secret" not in repr(params)
    db.get.assert_called_once()


def test_concurrent_profile_creation_converges_to_one_postgres_row(
    db_session, monkeypatch, tmp_path
):
    """Independent PostgreSQL sessions must converge on the deterministic profile."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import select, func
    from sqlalchemy.orm import sessionmaker

    from app.models.storage_profile import StorageProfile

    _require_isolated_local_test_database()
    test_engine = db_session.get_bind().engine
    sessions = sessionmaker(bind=test_engine, expire_on_commit=False)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "concurrent-profile"))
    monkeypatch.setattr(storage_profiles, "_s3_enabled", lambda: False)

    barrier = Barrier(2)

    def create_profile():
        with sessions() as session:
            barrier.wait(timeout=5)
            profile = storage_profiles.get_or_create_active_storage_profile(session)
            profile_id = profile.id
            session.commit()
            return profile_id

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(create_profile)
            second = executor.submit(create_profile)
            first_id = first.result(timeout=15)
            second_id = second.result(timeout=15)

        assert first_id == second_id
        with sessions() as session:
            count = session.scalar(
                select(func.count())
                .select_from(StorageProfile)
                .where(StorageProfile.id == first_id)
            )
            assert count == 1
            session.query(StorageProfile).filter(
                StorageProfile.id == first_id
            ).delete(synchronize_session=False)
            session.commit()
    finally:
        with sessions() as session:
            session.query(StorageProfile).filter(
                StorageProfile.root_path == str(tmp_path / "concurrent-profile")
            ).delete(synchronize_session=False)
            session.commit()
