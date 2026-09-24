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


def test_check_connection_calls_head_bucket(monkeypatch):
    for name, value in (
        ("S3_BUCKET", "bucket"),
        ("S3_ENDPOINT_URL", "https://s3.example.test"),
        ("S3_REGION", "us-west-004"),
        ("S3_ACCESS_KEY_ID", "key"),
        ("S3_SECRET_ACCESS_KEY", "secret"),
    ):
        monkeypatch.setattr(storage.settings, name, value)

    class FakeClient:
        def head_bucket(self, **kwargs):
            assert kwargs == {"Bucket": "bucket"}

    monkeypatch.setattr(storage, "_client", lambda: FakeClient())
    storage.check_connection()
