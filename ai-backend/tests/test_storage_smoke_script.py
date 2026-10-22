import importlib.util
import io
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "storage_smoke.py"
SPEC = importlib.util.spec_from_file_location("storage_smoke_under_test", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
storage_smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(storage_smoke)


def _configure_storage_env(monkeypatch):
    for name, value in (
        ("S3_BUCKET", "bucket"),
        ("S3_ENDPOINT_URL", "https://s3.example.test"),
        ("S3_REGION", "us-west-004"),
        ("S3_ACCESS_KEY_ID", "key"),
        ("S3_SECRET_ACCESS_KEY", "secret"),
    ):
        monkeypatch.setenv(name, value)


def _fake_storage(monkeypatch, *, read_error=None, upload_error=None, cleanup_error=None):
    objects = {}
    keys = []
    deleted = []

    def put_file(source, object_key, content_type):
        assert content_type == "text/plain"
        keys.append(object_key)
        objects[object_key] = Path(source).read_bytes()
        if upload_error is not None:
            raise upload_error

    def open_file(object_key, _fallback):
        if read_error is not None:
            raise read_error
        return io.BytesIO(objects[object_key])

    def delete_file(object_key, _fallback):
        deleted.append(object_key)
        if cleanup_error is not None:
            raise cleanup_error
        objects.pop(object_key, None)

    monkeypatch.setattr(storage_smoke, "check_connection", lambda: None)
    monkeypatch.setattr(storage_smoke, "put_file", put_file)
    monkeypatch.setattr(storage_smoke, "open_file", open_file)
    monkeypatch.setattr(storage_smoke, "delete_file", delete_file)
    return objects, keys, deleted


def test_smoke_uses_unique_object_key_and_cleans_up_on_success(monkeypatch):
    _configure_storage_env(monkeypatch)
    objects, keys, deleted = _fake_storage(monkeypatch)

    assert storage_smoke.main() == 0

    assert len(keys) == 1
    assert keys[0].startswith("smoke/ai-chat-app-storage-smoke-")
    assert keys[0].endswith(".txt")
    assert not objects
    assert deleted == keys


def test_smoke_cleans_up_if_read_back_fails(monkeypatch):
    _configure_storage_env(monkeypatch)
    read_error = RuntimeError("read-back failed")
    objects, keys, deleted = _fake_storage(monkeypatch, read_error=read_error)

    with pytest.raises(RuntimeError, match="read-back failed"):
        storage_smoke.main()

    assert len(keys) == 1
    assert deleted == keys
    assert not objects


def test_smoke_cleans_up_partial_upload_and_preserves_original_error(monkeypatch):
    _configure_storage_env(monkeypatch)
    upload_error = RuntimeError("upload interrupted")
    objects, keys, deleted = _fake_storage(monkeypatch, upload_error=upload_error)

    with pytest.raises(RuntimeError, match="upload interrupted"):
        storage_smoke.main()

    assert len(keys) == 1
    assert deleted == keys
    assert not objects


def test_cleanup_failure_after_success_fails_the_smoke(monkeypatch):
    _configure_storage_env(monkeypatch)
    objects, keys, deleted = _fake_storage(monkeypatch, cleanup_error=RuntimeError("delete denied"))

    with pytest.raises(RuntimeError, match="delete denied"):
        storage_smoke.main()

    assert len(keys) == 1
    assert deleted == keys
    # The remote object may remain when deletion fails; the test must report that failure.
    assert keys[0] in objects
