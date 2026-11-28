"""Unified file storage with S3-compatible object storage and local fallback."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
from pathlib import Path
from shutil import copyfileobj
from tempfile import NamedTemporaryFile
from typing import BinaryIO, Iterator

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings


class StorageError(RuntimeError):
    pass


def _local_bytes_path(object_key: str) -> Path:
    """Map an object key to an opaque, filesystem-safe local filename."""
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    generated_root = upload_root / ".generated-objects"
    try:
        generated_root.mkdir(parents=True, exist_ok=True)
        resolved_root = generated_root.resolve()
        if not resolved_root.is_relative_to(upload_root):
            raise StorageError("مسار التخزين غير صالح")
        filename = hashlib.sha256(object_key.encode("utf-8")).hexdigest()
        target = resolved_root / filename
        if target.is_symlink():
            raise StorageError("مسار التخزين غير صالح")
        return target
    except StorageError:
        raise
    except OSError as exc:
        raise StorageError("تعذر تجهيز مسار التخزين المحلي") from exc


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


def put_bytes(content: bytes, object_key: str, content_type: str) -> None:
    """Store small generated artifacts in object storage, with local fallback."""
    if not object_key or object_key.startswith("/") or ".." in Path(object_key).parts:
        raise StorageError("مسار التخزين غير صالح")
    if not _s3_enabled():
        target = _local_bytes_path(object_key)
        try:
            target.write_bytes(content)
        except OSError as exc:
            raise StorageError("فشل حفظ الملف المولد") from exc
        return
    try:
        _client().put_object(
            Bucket=settings.S3_BUCKET,
            Key=object_key,
            Body=content,
            ContentType=content_type,
        )
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("فشل رفع الملف المولد إلى Object Storage") from exc


def get_bytes(object_key: str, max_bytes: int | None = None) -> bytes:
    """Read bytes, optionally enforcing a hard size bound for generated artifacts."""
    if not object_key or object_key.startswith("/") or ".." in Path(object_key).parts:
        raise StorageError("مسار التخزين غير صالح")
    if max_bytes is not None and max_bytes < 0:
        raise StorageError("حد القراءة غير صالح")
    if not _s3_enabled():
        try:
            target = _local_bytes_path(object_key)
            if max_bytes is not None and target.stat().st_size > max_bytes:
                raise StorageError("الملف يتجاوز حد القراءة")
            return target.read_bytes()
        except StorageError:
            raise
        except OSError as exc:
            raise StorageError("تعذر قراءة الملف المولد") from exc
    body = None
    try:
        response = _client().get_object(Bucket=settings.S3_BUCKET, Key=object_key)
        body = response["Body"]
        if max_bytes is not None and response.get("ContentLength", max_bytes + 1) > max_bytes:
            raise StorageError("الملف يتجاوز حد القراءة")
        if max_bytes is None:
            return body.read()
        chunks = []
        total = 0
        while True:
            chunk = body.read(min(64 * 1024, max_bytes - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise StorageError("الملف يتجاوز حد القراءة")
            chunks.append(chunk)
        return b"".join(chunks)
    except StorageError:
        raise
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("تعذر قراءة الملف المولد من Object Storage") from exc
    finally:
        if body is not None:
            body.close()


def open_file(object_key: str, fallback_path: Path) -> BinaryIO:
    if not _s3_enabled():
        return fallback_path.open("rb")
    try:
        response = _client().get_object(Bucket=settings.S3_BUCKET, Key=object_key)
        return response["Body"]
    except ClientError as exc:
        # A local copy is a migration fallback only when the remote object is
        # definitively absent. Permission, bucket, and service errors must not
        # silently serve stale local bytes.
        error = exc.response.get("Error", {})
        error_code = str(error.get("Code", ""))
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if (
            error_code in {"NoSuchKey", "NotFound", "404"}
            and status_code == 404
            and fallback_path.exists()
        ):
            return fallback_path.open("rb")
        raise StorageError("فشل قراءة الملف من Object Storage") from exc
    except BotoCoreError as exc:
        raise StorageError("فشل قراءة الملف من Object Storage") from exc


@contextmanager
def materialize_file(object_key: str | None, fallback_path: Path) -> Iterator[Path]:
    """Provide a temporary local path for APIs that cannot consume a stream."""
    if not _s3_enabled():
        if not fallback_path.exists():
            raise FileNotFoundError(str(fallback_path))
        yield fallback_path
        return

    if object_key:
        source = open_file(object_key, fallback_path)
    elif fallback_path.exists():
        source = fallback_path.open("rb")
    else:
        raise FileNotFoundError(str(fallback_path))

    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            prefix="ai-chat-storage-",
            suffix=fallback_path.suffix or ".bin",
            delete=False,
        ) as temporary:
            temp_path = Path(temporary.name)
            copyfileobj(source, temporary)
        yield temp_path
    finally:
        source.close()
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def delete_user_objects(user_id: int) -> None:
    """Delete every remote object owned by a user, including orphaned uploads."""
    if not _s3_enabled():
        return

    prefix = f"users/{user_id}/"
    try:
        client = _client()
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=settings.S3_BUCKET, Prefix=prefix):
            contents = page.get("Contents") or []
            for start in range(0, len(contents), 1000):
                objects = [
                    {"Key": item["Key"]}
                    for item in contents[start : start + 1000]
                ]
                response = client.delete_objects(
                    Bucket=settings.S3_BUCKET,
                    Delete={"Objects": objects, "Quiet": True},
                )
                if response.get("Errors"):
                    raise StorageError(
                        "فشل حذف بعض ملفات المستخدم من Object Storage"
                    )
    except (BotoCoreError, ClientError) as exc:
        raise StorageError(
            "تعذر تنظيف ملفات المستخدم من Object Storage"
        ) from exc


def delete_file(object_key: str, fallback_path: Path) -> None:
    if _s3_enabled():
        try:
            _client().delete_object(Bucket=settings.S3_BUCKET, Key=object_key)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("فشل حذف الملف من Object Storage") from exc
    fallback_path.unlink(missing_ok=True)
