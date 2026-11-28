"""Focused unit tests for S3 object deletion and user-prefix isolation."""

from unittest.mock import MagicMock

import pytest

from app.config import settings
from app.services import storage
from app.services.storage import StorageError


def _enable_s3(monkeypatch):
    for name, value in (
        ("S3_BUCKET", "test-bucket"),
        ("S3_ENDPOINT_URL", "https://objects.example.test"),
        ("S3_REGION", "us-east-1"),
        ("S3_ACCESS_KEY_ID", "test-access-key"),
        ("S3_SECRET_ACCESS_KEY", "test-secret-key"),
    ):
        monkeypatch.setattr(settings, name, value)


def test_delete_file_uses_configured_bucket_and_object_key(tmp_path, monkeypatch):
    _enable_s3(monkeypatch)
    fallback = tmp_path / "upload.bin"
    fallback.write_bytes(b"local copy")
    client = MagicMock()
    monkeypatch.setattr(storage, "_client", lambda: client)

    storage.delete_file("users/42/upload.bin", fallback)

    client.delete_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="users/42/upload.bin",
    )
    assert not fallback.exists()


def test_delete_user_objects_uses_user_prefix_and_batches_at_1000(monkeypatch):
    _enable_s3(monkeypatch)
    keys = [f"users/42/file-{index}.bin" for index in range(1001)]
    paginator = MagicMock()
    paginator.paginate.return_value = [{"Contents": [{"Key": key} for key in keys]}]
    client = MagicMock()
    client.get_paginator.return_value = paginator
    client.delete_objects.return_value = {}
    monkeypatch.setattr(storage, "_client", lambda: client)

    storage.delete_user_objects(42)

    paginator.paginate.assert_called_once_with(
        Bucket="test-bucket",
        Prefix="users/42/",
    )
    assert [len(item.kwargs["Delete"]["Objects"]) for item in client.delete_objects.call_args_list] == [1000, 1]
    assert client.delete_objects.call_args_list[0].kwargs["Delete"]["Objects"] == [
        {"Key": key} for key in keys[:1000]
    ]
    assert client.delete_objects.call_args_list[1].kwargs["Delete"]["Objects"] == [
        {"Key": keys[1000]}
    ]
    assert all(
        key["Key"].startswith("users/42/")
        for item in client.delete_objects.call_args_list
        for key in item.kwargs["Delete"]["Objects"]
    )


def test_delete_user_objects_raises_storage_error_for_partial_s3_failures(monkeypatch):
    _enable_s3(monkeypatch)
    paginator = MagicMock()
    paginator.paginate.return_value = [
        {"Contents": [{"Key": "users/42/file.bin"}]}
    ]
    client = MagicMock()
    client.get_paginator.return_value = paginator
    client.delete_objects.return_value = {
        "Errors": [
            {
                "Key": "users/42/file.bin",
                "Code": "AccessDenied",
                "Message": "denied",
            }
        ]
    }
    monkeypatch.setattr(storage, "_client", lambda: client)

    with pytest.raises(StorageError, match="فشل حذف بعض ملفات المستخدم"):
        storage.delete_user_objects(42)


def test_delete_user_objects_never_requests_another_users_prefix(monkeypatch):
    _enable_s3(monkeypatch)
    paginator = MagicMock()
    paginator.paginate.return_value = [{"Contents": []}]
    client = MagicMock()
    client.get_paginator.return_value = paginator
    monkeypatch.setattr(storage, "_client", lambda: client)

    storage.delete_user_objects(42)

    paginator.paginate.assert_called_once_with(
        Bucket="test-bucket",
        Prefix="users/42/",
    )
    client.delete_objects.assert_not_called()
