"""Canonical project archive export/import with strict validation."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import BinaryIO

from app.models.project import WorkspaceProject
from app.schemas.project_archive import (
    PROJECT_ARCHIVE_SCHEMA_VERSION,
    ProjectArchiveManifest,
)


MAX_ARCHIVE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 10 * 1024 * 1024
MAX_FILES = 200
MAX_MEMORIES = 50
MAX_FILE_BYTES = 50_000
MANIFEST_PATH = "project.json"
MEMORIES_PATH = "memories.json"


class ProjectArchiveError(ValueError):
    """Raised when a project archive is invalid or unsafe."""


@dataclass(frozen=True)
class ImportedArchive:
    manifest: ProjectArchiveManifest
    files: list[tuple[str, str]]
    memories: list[str]


def _safe_path(path: str) -> str:
    if not path or len(path) > 512:
        raise ProjectArchiveError("مسار ملف المشروع غير صالح.")
    normalized = path.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ProjectArchiveError("أرشيف المشروع يحتوي مسارًا غير آمن.")
    return str(pure)


def _regular_file(info: zipfile.ZipInfo) -> bool:
    return ((info.external_attr >> 16) & 0o170000) != 0o120000


def _zip_bytes(write_archive) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        write_archive(archive)
    payload = buffer.getvalue()
    if len(payload) > MAX_ARCHIVE_BYTES:
        raise ProjectArchiveError("حجم تصدير المشروع يتجاوز الحد المسموح.")
    return payload


def build_project_export(
    project: WorkspaceProject,
    files: list,
    memories: list,
) -> bytes:
    ordered_files = sorted(files, key=lambda item: (item.path, item.id))
    if len(ordered_files) > MAX_FILES:
        raise ProjectArchiveError("المشروع يحتوي ملفات أكثر من الحد المسموح.")
    if len(memories) > MAX_MEMORIES:
        raise ProjectArchiveError("المشروع يحتوي ذكريات أكثر من الحد المسموح.")

    manifest_files = []
    file_payloads: list[tuple[str, bytes]] = []
    total_bytes = 0

    for item in ordered_files:
        content = item.content.encode("utf-8")
        if len(content) > MAX_FILE_BYTES:
            raise ProjectArchiveError(f"الملف {item.path} يتجاوز الحد المسموح.")
        safe_path = _safe_path(item.path)
        total_bytes += len(content)
        if total_bytes > MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise ProjectArchiveError("إجمالي ملفات المشروع يتجاوز الحد المسموح.")
        digest = hashlib.sha256(content).hexdigest()
        manifest_files.append(
            {
                "path": safe_path,
                "sha256": digest,
                "content_size": len(content),
            }
        )
        file_payloads.append((f"files/{safe_path}", content))

    manifest = {
        "schema_version": PROJECT_ARCHIVE_SCHEMA_VERSION,
        "project": {
            "name": project.name,
            "description": project.description,
            "instructions": project.instructions,
        },
        "files": manifest_files,
        "memories": [{"content": memory.content} for memory in memories],
    }

    def writer(archive: zipfile.ZipFile) -> None:
        def write_text(path: str, text: str) -> None:
            info = zipfile.ZipInfo(path, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, text.encode("utf-8"))

        write_text(
            MANIFEST_PATH,
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )
        write_text(
            MEMORIES_PATH,
            json.dumps(
                [{"content": memory.content} for memory in memories],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
        for path, content in file_payloads:
            info = zipfile.ZipInfo(path, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)

    return _zip_bytes(writer)


def parse_project_import(payload: BinaryIO | bytes) -> ImportedArchive:
    if hasattr(payload, "read"):
        raw = payload.read(MAX_ARCHIVE_BYTES + 1)
    else:
        raw = bytes(payload)

    if len(raw) > MAX_ARCHIVE_BYTES:
        raise ProjectArchiveError("أرشيف المشروع يتجاوز الحجم المسموح.")

    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise ProjectArchiveError("ملف الاستيراد ليس ZIP صالحًا.") from exc

    try:
        infos = archive.infolist()
        if len(infos) > MAX_FILES + 2:
            raise ProjectArchiveError("أرشيف المشروع يحتوي عناصر أكثر من الحد المسموح.")
        by_name: dict[str, zipfile.ZipInfo] = {}
        for info in infos:
            if info.is_dir() or not _regular_file(info):
                raise ProjectArchiveError("الأرشيف يحتوي رابطًا رمزيًا أو عنصرًا غير مدعوم.")
            path = _safe_path(info.filename)
            if path in by_name:
                raise ProjectArchiveError("الأرشيف يحتوي مسارًا مكررًا.")
            by_name[path] = info

        if MANIFEST_PATH not in by_name:
            raise ProjectArchiveError("الأرشيف يفتقد project.json.")

        manifest_raw = archive.read(by_name[MANIFEST_PATH])
        try:
            manifest = ProjectArchiveManifest.model_validate_json(manifest_raw)
        except ValueError as exc:
            raise ProjectArchiveError("project.json غير صالح.") from exc

        if manifest.schema_version != PROJECT_ARCHIVE_SCHEMA_VERSION:
            raise ProjectArchiveError(
                f"إصدار archive غير مدعوم: {manifest.schema_version}."
            )

        if len(manifest.files) > MAX_FILES or len(manifest.memories) > MAX_MEMORIES:
            raise ProjectArchiveError("الـmanifest يتجاوز حدود المشروع.")

        expected_paths = {f"files/{item.path}" for item in manifest.files}
        actual_paths = {path for path in by_name if path.startswith("files/")}
        if expected_paths != actual_paths:
            raise ProjectArchiveError("ملفات الأرشيف لا تطابق manifest.")

        files: list[tuple[str, str]] = []
        total_bytes = 0
        for item in manifest.files:
            info = by_name[f"files/{item.path}"]
            if info.file_size > MAX_FILE_BYTES:
                raise ProjectArchiveError(f"الملف {item.path} يتجاوز الحد المسموح.")
            content = archive.read(info)
            if len(content) != info.file_size:
                raise ProjectArchiveError("حجم ملف الأرشيف غير متطابق.")
            total_bytes += len(content)
            if total_bytes > MAX_TOTAL_UNCOMPRESSED_BYTES:
                raise ProjectArchiveError("إجمالي ملفات الأرشيف يتجاوز الحد.")
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ProjectArchiveError(f"الملف {item.path} ليس UTF-8 صالحًا.") from exc
            if len(content) != item.content_size:
                raise ProjectArchiveError(f"حجم {item.path} لا يطابق manifest.")
            if hashlib.sha256(content).hexdigest() != item.sha256:
                raise ProjectArchiveError(f"checksum غير صحيح للملف {item.path}.")
            files.append((item.path, text))

        memories: list[str] = []
        if MEMORIES_PATH in by_name:
            try:
                parsed_memories = json.loads(archive.read(by_name[MEMORIES_PATH]))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ProjectArchiveError("memories.json غير صالح.") from exc
            if not isinstance(parsed_memories, list) or len(parsed_memories) > MAX_MEMORIES:
                raise ProjectArchiveError("memories.json غير صالح.")
            for value in parsed_memories:
                if not isinstance(value, dict) or not isinstance(value.get("content"), str):
                    raise ProjectArchiveError("صيغة ذاكرة المشروع غير صالحة.")
                content = value["content"].strip()
                if not content or len(content) > 1000:
                    raise ProjectArchiveError("محتوى ذاكرة المشروع غير صالح.")
                memories.append(content)

        unexpected = set(by_name) - expected_paths - {MANIFEST_PATH, MEMORIES_PATH}
        if unexpected:
            raise ProjectArchiveError("الأرشيف يحتوي ملفات غير مدعومة.")
        return ImportedArchive(manifest=manifest, files=files, memories=memories)
    finally:
        archive.close()
