"""Tests for immutable storage-profile identity capture."""
from unittest.mock import MagicMock

import pytest

from app.config import settings
from app.services import storage_profiles


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
