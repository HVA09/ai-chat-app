"""Client for an isolated project preview builder.

This module deliberately does not execute project build commands. It only sends
validated project source to a separately deployed builder service when explicitly
configured. Production stays fail-closed unless the builder URL is HTTPS and a
shared token is configured.
"""

from __future__ import annotations

import re
from typing import Iterable

import httpx

from app.config import settings
from app.schemas.project_preview import (
    PreviewBuildFile,
    PreviewBuildRequest,
    PreviewBuildResponse,
)

_SECRET_FILENAME_RE = re.compile(r"(^|/)\.env(\.[^./]+)?$", re.IGNORECASE)
_PRIVATE_KEY_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
_ALLOWED_BUILD_COMMAND = "npm run build"


class PreviewBuilderError(RuntimeError):
    """Raised when a preview builder request is invalid or unavailable."""


def _validate_files(files: Iterable[PreviewBuildFile]) -> list[PreviewBuildFile]:
    normalized: list[PreviewBuildFile] = []
    seen: set[str] = set()
    total_chars = 0

    for item in files:
        path = item.path.replace("\\", "/").strip()
        if not path or path.startswith("/") or ".." in path.split("/"):
            raise PreviewBuilderError(f"مسار ملف غير آمن: {item.path}")
        if _SECRET_FILENAME_RE.search(path) and path.lower() != ".env.example":
            raise PreviewBuilderError(f"ملف أسرار غير مسموح إرساله إلى builder: {path}")
        if path.lower().endswith(_PRIVATE_KEY_SUFFIXES):
            raise PreviewBuilderError(f"ملف مفاتيح خاصة غير مسموح: {path}")
        if "\x00" in item.content:
            raise PreviewBuilderError(f"محتوى ثنائي غير مسموح: {path}")
        if len(item.content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise PreviewBuilderError(f"الملف كبير جدًا: {path}")
        if path in seen:
            raise PreviewBuilderError(f"المسار مكرر: {path}")
        seen.add(path)
        total_chars += len(item.content)
        if total_chars > settings.PREVIEW_MAX_TOTAL_CHARS:
            raise PreviewBuilderError("إجمالي محتوى المشروع يتجاوز حد المعاينة.")
        normalized.append(PreviewBuildFile(path=path, content=item.content))

    if len(normalized) > settings.PREVIEW_MAX_FILES:
        raise PreviewBuilderError("عدد ملفات المشروع يتجاوز حد المعاينة.")
    if not any(item.path.lower() == "package.json" for item in normalized):
        raise PreviewBuilderError("لا يمكن إنشاء JavaScript preview بدون package.json.")
    return normalized


def _builder_url() -> str:
    url = settings.PREVIEW_BUILDER_URL.strip().rstrip("/")
    if not url:
        raise PreviewBuilderError("خدمة preview builder غير مهيأة.")
    if settings.ENVIRONMENT == "production" and not url.startswith("https://"):
        raise PreviewBuilderError("خدمة preview builder يجب أن تستخدم HTTPS.")
    return url


async def build_javascript_preview(
    project_id: int,
    files: Iterable[PreviewBuildFile],
) -> PreviewBuildResponse:
    """Request a build from a separate, isolated builder service.

    The backend never shells out to npm/node and never executes project code.
    """
    if _ALLOWED_BUILD_COMMAND != "npm run build":
        raise PreviewBuilderError("استراتيجية build غير مسموحة.")

    url = _builder_url()
    token = settings.PREVIEW_BUILDER_TOKEN.strip()
    if not token:
        raise PreviewBuilderError("رمز preview builder غير مهيأ.")

    normalized_files = _validate_files(files)
    payload = PreviewBuildRequest(
        project_id=project_id,
        project_kind="javascript",
        files=normalized_files,
        build_command=_ALLOWED_BUILD_COMMAND,
    )

    try:
        timeout = httpx.Timeout(settings.PREVIEW_BUILD_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{url}/v1/build",
                json=payload.model_dump(),
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Preview-Protocol": "1",
                },
            )
    except httpx.HTTPError as exc:
        raise PreviewBuilderError("تعذر الاتصال بخدمة preview builder.") from exc

    if response.status_code in {401, 403}:
        raise PreviewBuilderError("رفضت خدمة preview builder الطلب.")
    if response.status_code != 200:
        raise PreviewBuilderError(
            f"فشل بناء المعاينة (HTTP {response.status_code})."
        )

    try:
        result = PreviewBuildResponse.model_validate(response.json())
    except ValueError as exc:
        raise PreviewBuilderError("أعاد builder استجابة غير صالحة.") from exc

    allowed_entrypoint = (
        result.entrypoint == "index.html"
        or result.entrypoint.startswith(("dist/", "build/"))
    )
    if not allowed_entrypoint:
        raise PreviewBuilderError("نقطة دخول artifact غير مسموحة.")
    try:
        artifact_size = len(result.artifact_base64.encode("ascii"))
    except UnicodeEncodeError as exc:
        raise PreviewBuilderError("artifact غير صالح.") from exc
    if artifact_size > int(settings.PREVIEW_MAX_ARTIFACT_BYTES * 1.34):
        raise PreviewBuilderError("artifact الناتج أكبر من الحد المسموح.")

    return result
