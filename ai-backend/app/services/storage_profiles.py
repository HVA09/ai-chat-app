"""Resolve and persist immutable, non-secret storage backend identities."""
from __future__ import annotations

import hashlib
import json
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models.storage_profile import StorageProfile
from app.services.storage import _s3_enabled


def _safe_endpoint(value: str) -> str:
    """Preserve endpoint base paths without persisting URL credentials."""
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("S3_ENDPOINT_URL contains an invalid port") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("S3_ENDPOINT_URL must be a credential-free HTTP(S) URL")
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if port is not None:
        host = f"{host}:{port}"
    return urlunsplit((parsed.scheme.lower(), host, parsed.path.rstrip("/"), "", ""))


def active_storage_profile_identity() -> tuple[str, dict]:
    """Return the deterministic identity and safe persisted fields for current config."""
    if _s3_enabled():
        identity = {
            "provider": "s3",
            "bucket": settings.S3_BUCKET,
            "endpoint_url": _safe_endpoint(settings.S3_ENDPOINT_URL),
            "region": settings.S3_REGION,
            "root_path": None,
            "credential_ref": "env:S3_ACCESS_KEY_ID+S3_SECRET_ACCESS_KEY",
        }
    else:
        identity = {
            "provider": "local",
            "bucket": None,
            "endpoint_url": None,
            "region": None,
            "root_path": str(settings.UPLOAD_DIR),
            "credential_ref": None,
        }
    profile_id = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return profile_id, identity


def get_or_create_active_storage_profile(db: Session) -> StorageProfile:
    """Capture the active backend identity; legacy rows remain unclassified."""
    profile_id, identity = active_storage_profile_identity()
    statement = (
        insert(StorageProfile)
        .values(id=profile_id, **identity)
        .on_conflict_do_nothing(index_elements=[StorageProfile.id])
    )
    db.execute(statement)
    profile = db.get(StorageProfile, profile_id)
    if profile is None:
        raise RuntimeError("Storage profile insert did not produce a readable row")
    return profile
