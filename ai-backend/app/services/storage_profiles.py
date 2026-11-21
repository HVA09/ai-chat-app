"""Resolve and persist immutable, non-secret storage backend identities."""
import hashlib, json
from urllib.parse import urlsplit
from sqlalchemy.orm import Session
from app.config import settings
from app.models.storage_profile import StorageProfile
from app.services.storage import _s3_enabled

def _safe_endpoint(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("S3_ENDPOINT_URL must be a credential-free HTTP(S) URL")
    return f"{parsed.scheme}://{parsed.netloc}"

def get_or_create_active_storage_profile(db: Session) -> StorageProfile:
    # Legacy rows remain NULL: current configuration cannot prove their historical backend.
    if _s3_enabled():
        identity = {"provider":"s3","bucket":settings.S3_BUCKET,"endpoint_url":_safe_endpoint(settings.S3_ENDPOINT_URL),"region":settings.S3_REGION,"root_path":None,"credential_ref":"env:S3_ACCESS_KEY_ID+S3_SECRET_ACCESS_KEY"}
    else:
        identity = {"provider":"local","bucket":None,"endpoint_url":None,"region":None,"root_path":str(settings.UPLOAD_DIR),"credential_ref":None}
    profile_id = hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    profile = db.get(StorageProfile, profile_id)
    if profile is None:
        profile = StorageProfile(id=profile_id, **identity)
        db.add(profile)
        db.flush()
    return profile
