#!/usr/bin/env python3
"""One-shot Object Storage smoke test using the application's storage adapter."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql://smoke:smoke@127.0.0.1:5432/smoke")
os.environ.setdefault("JWT_SECRET_KEY", "smoke-jwt-secret")
os.environ.setdefault("AI_API_KEY", "smoke-ai-key")
os.environ.setdefault("S3_BUCKET", os.environ.get("B2_BUCKET", ""))
os.environ.setdefault("S3_ENDPOINT_URL", os.environ.get("B2_ENDPOINT_URL", ""))
os.environ.setdefault("S3_REGION", os.environ.get("B2_REGION", ""))
os.environ.setdefault("S3_ACCESS_KEY_ID", os.environ.get("B2_KEY_ID", ""))
os.environ.setdefault("S3_SECRET_ACCESS_KEY", os.environ.get("B2_APPLICATION_KEY", ""))

from app.services.storage import StorageError, check_connection, delete_file, open_file, put_file


def main() -> int:
    required = (
        "S3_BUCKET",
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise SystemExit("Missing storage configuration: " + ", ".join(missing))

    check_connection()

    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "storage-smoke.txt"
        fallback = Path(tmp) / "fallback.txt"
        payload = b"ai-chat-app backblaze b2 storage smoke test"
        source.write_bytes(payload)
        # Unique keys avoid collisions between concurrent/manual smoke runs.
        object_key = f"smoke/ai-chat-app-storage-smoke-{uuid4().hex}.txt"

        try:
            put_file(source, object_key, "text/plain")

            remote = open_file(object_key, fallback)
            try:
                received = remote.read()
            finally:
                remote.close()

            if received != payload:
                raise StorageError("Object Storage read-back payload mismatch")
        except BaseException:
            # Cleanup is best-effort when the smoke itself already failed.
            # Preserve the original exception so it remains the primary signal.
            try:
                delete_file(object_key, fallback)
            except Exception as cleanup_error:
                print(
                    f"WARNING: failed to clean up smoke object: {cleanup_error}",
                    file=sys.stderr,
                )
            raise
        else:
            # A cleanup failure after a successful round-trip should fail the smoke.
            delete_file(object_key, fallback)

    print("Object Storage smoke PASSED: upload -> read-back -> delete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
