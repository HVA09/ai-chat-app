"""Secure publication and serving helpers for built project previews.

Built artifacts are never executed by the backend. This module extracts only
regular files from the builder ZIP, stores them under a project-scoped key, and
issues short-lived bearer tokens for the sandboxed preview route.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import mimetypes
import re
import time
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import quote

from app.config import settings
from app.schemas.project_preview import PreviewBuildResponse
from app.services.storage import StorageError, delete_prefix, get_bytes, put_bytes

_MAX_PATH_LENGTH = 512
_TOKEN_VERSION = "v1"
_ABSOLUTE_URL_RE = re.compile(
    r'(?P<prefix>\b(?:src|href|poster)\s*=\s*["\']|url\(\s*[\'"]?)(?P<path>/[^\s"\'\)]+)'
)
_EXTERNAL_URL_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)


class PreviewArtifactError(RuntimeError):
    """Raised when a built artifact cannot be published or served safely."""


@dataclass(frozen=True)
class PublishedPreview:
    artifact_id: str
    token: str
    expires_at: int
    entrypoint: str


def _safe_zip_path(name: str) -> str:
    if not name or len(name) > _MAX_PATH_LENGTH:
        raise PreviewArtifactError("مسار artifact غير صالح.")
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PreviewArtifactError("artifact يحتوي مسارًا غير آمن.")
    return str(path)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return (info.external_attr >> 16) & 0o170000 == 0o120000


def _sign(payload: str) -> str:
    digest = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def issue_preview_token(
    project_id: int,
    artifact_id: str,
    artifact_root: str,
) -> tuple[str, int]:
    expires_at = int(time.time()) + settings.PREVIEW_TOKEN_TTL_SECONDS
    root_token = base64.urlsafe_b64encode(artifact_root.encode("utf-8")).decode("ascii").rstrip("=")
    payload = f"{_TOKEN_VERSION}.{project_id}.{artifact_id}.{expires_at}.{root_token}"
    return f"{payload}.{_sign(payload)}", expires_at


def verify_preview_token(project_id: int, artifact_id: str, token: str) -> str:
    parts = token.split(".")
    if len(parts) != 6 or parts[0] != _TOKEN_VERSION:
        raise PreviewArtifactError("رمز المعاينة غير صالح.")
    _, token_project, token_artifact, token_expiry, root_token, signature = parts
    if token_project != str(project_id) or token_artifact != artifact_id:
        raise PreviewArtifactError("رمز المعاينة لا يطابق المشروع.")
    try:
        expires_at = int(token_expiry)
    except ValueError as exc:
        raise PreviewArtifactError("رمز المعاينة غير صالح.") from exc
    if expires_at < int(time.time()):
        raise PreviewArtifactError("انتهت صلاحية المعاينة.")
    payload = ".".join(parts[:-1])
    if not hmac.compare_digest(signature, _sign(payload)):
        raise PreviewArtifactError("توقيع المعاينة غير صالح.")
    try:
        return base64.urlsafe_b64decode(root_token + "=" * (-len(root_token) % 4)).decode("utf-8")
    except Exception as exc:
        raise PreviewArtifactError("رمز المعاينة يحتوي مجلدًا غير صالح.") from exc


def artifact_storage_prefix(project_id: int, artifact_id: str) -> str:
    if not artifact_id or not re.fullmatch(r"[0-9a-f]{32}", artifact_id):
        raise PreviewArtifactError("معرّف artifact غير صالح.")
    return f"previews/{project_id}/{artifact_id}"


def _object_key(project_id: int, artifact_id: str, path: str) -> str:
    return f"{artifact_storage_prefix(project_id, artifact_id)}/{path}"


def delete_preview_artifact(project_id: int, artifact_id: str) -> None:
    try:
        delete_prefix(artifact_storage_prefix(project_id, artifact_id))
    except StorageError as exc:
        raise PreviewArtifactError("تعذر حذف artifact المعاينة.") from exc


def publish_preview_artifact(
    project_id: int,
    build: PreviewBuildResponse,
) -> PublishedPreview:
    try:
        artifact = base64.b64decode(build.artifact_base64, validate=True)
    except Exception as exc:
        raise PreviewArtifactError("artifact المشفر غير صالح.") from exc

    if len(artifact) != build.artifact_size_bytes:
        raise PreviewArtifactError("حجم artifact لا يطابق بيانات البناء.")
    if len(artifact) > settings.PREVIEW_MAX_ARTIFACT_BYTES:
        raise PreviewArtifactError("artifact يتجاوز الحجم المسموح.")

    artifact_id = hashlib.sha256(artifact).hexdigest()[:32]
    total_bytes = 0
    files: dict[str, tuple[bytes, str]] = {}

    try:
        with zipfile.ZipFile(io.BytesIO(artifact)) as archive:
            infos = archive.infolist()
            if len(infos) > settings.PREVIEW_MAX_FILES:
                raise PreviewArtifactError("artifact يحتوي ملفات أكثر من الحد المسموح.")
            for info in infos:
                if info.is_dir():
                    continue
                if _is_symlink(info):
                    raise PreviewArtifactError("artifact يحتوي رابطًا رمزيًا غير مسموح.")
                path = _safe_zip_path(info.filename)
                total_bytes += info.file_size
                if total_bytes > settings.PREVIEW_MAX_ARTIFACT_BYTES:
                    raise PreviewArtifactError("الحجم الإجمالي للملفات يتجاوز الحد المسموح.")
                content = archive.read(info)
                if len(content) != info.file_size:
                    raise PreviewArtifactError("تعذر التحقق من حجم ملف artifact.")
                files[path] = (content, mimetypes.guess_type(path)[0] or "application/octet-stream")
    except zipfile.BadZipFile as exc:
        raise PreviewArtifactError("artifact ليس ZIP صالحًا.") from exc

    entrypoint = _safe_zip_path(build.entrypoint)
    if entrypoint not in files:
        raise PreviewArtifactError("نقطة الدخول غير موجودة داخل artifact.")
    if not (
        entrypoint == "index.html"
        or entrypoint.startswith("dist/")
        or entrypoint.startswith("build/")
    ):
        raise PreviewArtifactError("نقطة الدخول ليست ضمن المسارات المسموح بها.")

    try:
        for path, (content, content_type) in files.items():
            put_bytes(
                content,
                _object_key(project_id, artifact_id, path),
                content_type,
            )
    except StorageError as exc:
        raise PreviewArtifactError("تعذر نشر artifact المعاينة.") from exc

    artifact_root = entrypoint.rsplit("/", 1)[0] if "/" in entrypoint else ""
    token, expires_at = issue_preview_token(project_id, artifact_id, artifact_root)
    return PublishedPreview(
        artifact_id=artifact_id,
        token=token,
        expires_at=expires_at,
        entrypoint=entrypoint,
    )


def read_preview_file(project_id: int, artifact_id: str, path: str) -> tuple[bytes, str]:
    safe_path = _safe_zip_path(path)
    try:
        content = get_bytes(_object_key(project_id, artifact_id, safe_path))
    except StorageError as exc:
        raise PreviewArtifactError("تعذر قراءة artifact المعاينة.") from exc
    content_type = mimetypes.guess_type(safe_path)[0] or "application/octet-stream"
    return content, content_type


def preview_url_path(project_id: int, artifact_id: str, token: str, entrypoint: str) -> str:
    safe_entrypoint = _safe_zip_path(entrypoint)
    return (
        f"/projects/{project_id}/preview-artifacts/"
        f"{artifact_id}/{quote(token, safe='')}/{quote(safe_entrypoint, safe='/')}"
    )


def rewrite_absolute_preview_urls(
    html: str,
    project_id: int,
    artifact_id: str,
    token: str,
    artifact_root: str = "",
) -> str:
    prefix = f"/projects/{project_id}/preview-artifacts/{artifact_id}/{quote(token, safe='')}"
    if artifact_root:
        prefix += f"/{quote(artifact_root, safe='')}"

    def replace(match: re.Match[str]) -> str:
        path = match.group("path")
        if _EXTERNAL_URL_RE.match(path):
            return match.group(0)
        encoded_path = quote(
            path.lstrip("/"),
            safe="/%:@-._~!$&'()*+,;=",
        )
        return f"{match.group('prefix')}{prefix}/{encoded_path}"

    return _ABSOLUTE_URL_RE.sub(replace, html)


def preview_csp(frontend_origins: list[str]) -> str:
    frame_ancestors = " ".join(origin.rstrip("/") for origin in frontend_origins if origin)
    return (
        "default-src 'none'; "
        "script-src 'self' 'unsafe-inline' blob:; "
        "style-src 'self' 'unsafe-inline' blob:; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data: blob:; "
        "media-src 'self' data: blob:; "
        "connect-src 'none'; "
        "frame-src 'none'; "
        "worker-src 'self' blob:; "
        "object-src 'none'; "
        "base-uri 'none'; "
        "form-action 'none'; "
        "sandbox allow-scripts; "
        + (f"frame-ancestors {frame_ancestors};" if frame_ancestors else "frame-ancestors 'none';")
    )
