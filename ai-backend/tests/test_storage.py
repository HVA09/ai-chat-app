from pathlib import Path

from app.services import storage


def test_local_storage_round_trip(tmp_path, monkeypatch):
    for name in (
        "S3_BUCKET",
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    ):
        monkeypatch.setattr(storage.settings, name, "")

    path = tmp_path / "example.txt"
    path.write_text("hello", encoding="utf-8")

    storage.put_file(path, "users/1/example.txt", "text/plain")
    body = storage.open_file("users/1/example.txt", path)
    assert body.read() == b"hello"
    body.close()

    storage.delete_file("users/1/example.txt", path)
    assert not path.exists()


def test_s3_requires_complete_configuration(monkeypatch):
    monkeypatch.setattr(storage.settings, "S3_BUCKET", "bucket")
    monkeypatch.setattr(storage.settings, "S3_ENDPOINT_URL", "https://s3.example.test")
    monkeypatch.setattr(storage.settings, "S3_REGION", "")
    monkeypatch.setattr(storage.settings, "S3_ACCESS_KEY_ID", "key")
    monkeypatch.setattr(storage.settings, "S3_SECRET_ACCESS_KEY", "secret")
    assert storage._s3_enabled() is False


def test_s3_client_uses_sigv4(monkeypatch):
    monkeypatch.setattr(storage.settings, "S3_BUCKET", "bucket")
    monkeypatch.setattr(storage.settings, "S3_ENDPOINT_URL", "https://s3.example.test")
    monkeypatch.setattr(storage.settings, "S3_REGION", "us-west-004")
    monkeypatch.setattr(storage.settings, "S3_ACCESS_KEY_ID", "key")
    monkeypatch.setattr(storage.settings, "S3_SECRET_ACCESS_KEY", "secret")

    seen = {}

    class FakeBoto3:
        def client(self, service, **kwargs):
            seen["service"] = service
            seen["kwargs"] = kwargs
            return object()

    monkeypatch.setattr(storage, "boto3", FakeBoto3())
    client = storage._client()

    assert client is not None
    assert seen["service"] == "s3"
    assert seen["kwargs"]["endpoint_url"] == "https://s3.example.test"
    assert seen["kwargs"]["region_name"] == "us-west-004"
    assert seen["kwargs"]["aws_access_key_id"] == "key"
    assert seen["kwargs"]["aws_secret_access_key"] == "secret"
    assert seen["kwargs"]["config"].signature_version == "s3v4"


def test_check_connection_lists_bucket_with_file_listing_permission(monkeypatch):
    for name, value in (
        ("S3_BUCKET", "bucket"),
        ("S3_ENDPOINT_URL", "https://s3.example.test"),
        ("S3_REGION", "us-west-004"),
        ("S3_ACCESS_KEY_ID", "key"),
        ("S3_SECRET_ACCESS_KEY", "secret"),
    ):
        monkeypatch.setattr(storage.settings, name, value)

    class FakeClient:
        def list_objects_v2(self, **kwargs):
            assert kwargs == {"Bucket": "bucket", "MaxKeys": 1}

    monkeypatch.setattr(storage, "_client", lambda: FakeClient())
    storage.check_connection()

def _enable_s3(monkeypatch):
    for name, value in (
        ("S3_BUCKET", "bucket"),
        ("S3_ENDPOINT_URL", "https://s3.example.test"),
        ("S3_REGION", "us-west-004"),
        ("S3_ACCESS_KEY_ID", "key"),
        ("S3_SECRET_ACCESS_KEY", "secret"),
    ):
        monkeypatch.setattr(storage.settings, name, value)


def test_materialize_file_uses_local_fallback_without_s3(monkeypatch, tmp_path):
    for name in (
        "S3_BUCKET",
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    ):
        monkeypatch.setattr(storage.settings, name, "")

    fallback = tmp_path / "example.csv"
    fallback.write_bytes(b"local data")

    with storage.materialize_file(None, fallback) as materialized:
        assert materialized == fallback
        assert materialized.read_bytes() == b"local data"

    assert fallback.exists()


def test_materialize_file_uses_and_cleans_temporary_remote_file(monkeypatch, tmp_path):
    import io

    _enable_s3(monkeypatch)
    fallback = tmp_path / "example.csv"
    fallback.write_bytes(b"stale local data")
    body = io.BytesIO(b"remote data")
    monkeypatch.setattr(storage, "open_file", lambda key, path: body)

    with storage.materialize_file("users/1/example.csv", fallback) as materialized:
        assert materialized != fallback
        assert materialized.read_bytes() == b"remote data"
        assert materialized.exists()

    assert not materialized.exists()
    assert fallback.read_bytes() == b"stale local data"
    assert body.closed


def test_delete_user_objects_batches_large_prefix(monkeypatch):
    _enable_s3(monkeypatch)
    keys = [f"users/42/{index}.txt" for index in range(1001)]
    deleted_batches = []

    class FakePaginator:
        def paginate(self, **kwargs):
            assert kwargs == {"Bucket": "bucket", "Prefix": "users/42/"}
            return [{"Contents": [{"Key": key} for key in keys]}]

    class FakeClient:
        def get_paginator(self, name):
            assert name == "list_objects_v2"
            return FakePaginator()

        def delete_objects(self, **kwargs):
            batch = kwargs["Delete"]["Objects"]
            assert len(batch) <= 1000
            assert all(item["Key"].startswith("users/42/") for item in batch)
            deleted_batches.append([item["Key"] for item in batch])
            return {"Errors": []}

    monkeypatch.setattr(storage, "_client", lambda: FakeClient())

    storage.delete_user_objects(42)

    assert [len(batch) for batch in deleted_batches] == [1000, 1]
    assert [key for batch in deleted_batches for key in batch] == keys


def test_delete_user_objects_raises_when_remote_delete_reports_errors(monkeypatch):
    import pytest

    _enable_s3(monkeypatch)

    class FakePaginator:
        def paginate(self, **kwargs):
            return [{"Contents": [{"Key": "users/42/orphan.txt"}]}]

    class FakeClient:
        def get_paginator(self, name):
            return FakePaginator()

        def delete_objects(self, **kwargs):
            return {"Errors": [{"Key": "users/42/orphan.txt", "Code": "AccessDenied"}]}

    monkeypatch.setattr(storage, "_client", lambda: FakeClient())

    with pytest.raises(storage.StorageError):
        storage.delete_user_objects(42)


def test_delete_user_objects_is_noop_without_s3(monkeypatch):
    for name in (
        "S3_BUCKET",
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    ):
        monkeypatch.setattr(storage.settings, name, "")

    def unexpected_client():
        raise AssertionError("S3 client should not be constructed")

    monkeypatch.setattr(storage, "_client", unexpected_client)

    storage.delete_user_objects(42)
