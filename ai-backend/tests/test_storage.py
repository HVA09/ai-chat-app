from contextlib import contextmanager
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


def test_delete_user_objects_removes_all_remote_objects(monkeypatch):
    for name, value in (
        ("S3_BUCKET", "bucket"),
        ("S3_ENDPOINT_URL", "https://s3.example.test"),
        ("S3_REGION", "us-west-004"),
        ("S3_ACCESS_KEY_ID", "key"),
        ("S3_SECRET_ACCESS_KEY", "secret"),
    ):
        monkeypatch.setattr(storage.settings, name, value)

    deleted = []

    class FakePaginator:
        def paginate(self, **kwargs):
            assert kwargs == {"Bucket": "bucket", "Prefix": "users/42/"}
            return [{"Contents": [{"Key": "users/42/a.txt"}, {"Key": "users/42/b.zip"}]}]

    class FakeClient:
        def get_paginator(self, name):
            assert name == "list_objects_v2"
            return FakePaginator()

        def delete_objects(self, **kwargs):
            deleted.extend(item["Key"] for item in kwargs["Delete"]["Objects"])
            return {"Errors": []}

    monkeypatch.setattr(storage, "_client", lambda: FakeClient())

    storage.delete_user_objects(42)

    assert deleted == ["users/42/a.txt", "users/42/b.zip"]


def test_materialize_file_prefers_remote_storage(monkeypatch, tmp_path):
    for name, value in (
        ("S3_BUCKET", "bucket"),
        ("S3_ENDPOINT_URL", "https://s3.example.test"),
        ("S3_REGION", "us-west-004"),
        ("S3_ACCESS_KEY_ID", "key"),
        ("S3_SECRET_ACCESS_KEY", "secret"),
    ):
        monkeypatch.setattr(storage.settings, name, value)

    fallback = tmp_path / "example.pdf"
    fallback.write_bytes(b"local")

    class FakeBody:
        def read(self, size=-1):
            return b"remote"

        def close(self):
            pass

    monkeypatch.setattr(storage, "open_file", lambda key, path: FakeBody())

    class FakeTempFile:
        name = "virtual-remote.pdf"

        def __enter__(self):
            self.buffer = bytearray()
            return self

        def write(self, data):
            self.buffer.extend(data)
            return len(data)

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakePath:
        def __init__(self, value):
            self.value = value

        def read_bytes(self):
            return b"remote"

        def unlink(self, missing_ok=False):
            self.unlinked = True

        def __eq__(self, other):
            return isinstance(other, FakePath) and self.value == other.value

    monkeypatch.setattr(storage, "NamedTemporaryFile", lambda **kwargs: FakeTempFile())
    monkeypatch.setattr(storage, "Path", FakePath)

    with storage.materialize_file("users/1/example.pdf", fallback) as materialized:
        assert materialized.value == "virtual-remote.pdf"
        assert materialized.value != str(fallback)
        assert materialized.read_bytes() == b"remote"
