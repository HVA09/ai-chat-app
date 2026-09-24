"""Unified file storage with S3-compatible object storage and local fallback."""
from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings


class StorageError(RuntimeError):
    pass


def _s3_enabled() -> bool:
    """Enable remote storage only when all required connection settings exist."""
    return all(
        (
            settings.S3_BUCKET,
            settings.S3_ENDPOINT_URL,
            settings.S3_REGION,
            settings.S3_ACCESS_KEY_ID,
            settings.S3_SECRET_ACCESS_KEY,
        )
    )


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )


def check_connection() -> None:
    """Verify the configured remote bucket is reachable."""
    if not _s3_enabled():
        return
    try:
        _client().list_objects_v2(Bucket=settings.S3_BUCKET, MaxKeys=1)
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("تعذر الاتصال بـ Object Storage") from exc


def put_file(path: Path, object_key: str, content_type: str) -> None:
    if not _s3_enabled():
        return
    try:
        with path.open("rb") as source:
            _client().upload_fileobj(
                source,
                settings.S3_BUCKET,
                object_key,
                ExtraArgs={"ContentType": content_type},
            )
    except (BotoCoreError, ClientError, OSError) as exc:
        raise StorageError("فشل رفع الملف إلى Object Storage") from exc


def open_file(object_key: str, fallback_path: Path) -> BinaryIO:
    if not _s3_enabled():
        return fallback_path.open("rb")
    try:
        response = _client().get_object(Bucket=settings.S3_BUCKET, Key=object_key)
        return response["Body"]
    except (BotoCoreError, ClientError) as exc:
        # Keep existing local uploads readable during migration.
        if fallback_path.exists():
            return fallback_path.open("rb")
        raise StorageError("فشل قراءة الملف من Object Storage") from exc


def delete_file(object_key: str, fallback_path: Path) -> None:
    if _s3_enabled():
        try:
            _client().delete_object(Bucket=settings.S3_BUCKET, Key=object_key)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("فشل حذف الملف من Object Storage") from exc
    fallback_path.unlink(missing_ok=True)
