import base64
import io
import zipfile
import json

import pytest

from app.models.project_file import ProjectFile
from app.models.project_memory import ProjectMemory
from app.services.project_archive import (
    ProjectArchiveError,
    build_project_export,
    parse_project_import,
)


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in entries.items():
            archive.writestr(path, content)
    return buffer.getvalue()


def test_project_archive_round_trip_is_canonical(db_session, client):
    token = client.post(
        "/auth/register",
        json={"email": "archive-roundtrip@example.com", "password": "StrongPass123"},
    )
    assert token.status_code == 201
    login = client.post(
        "/auth/login",
        json={"email": "archive-roundtrip@example.com", "password": "StrongPass123"},
    )
    access_token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Archives"},
        headers=headers,
    ).json()
    project = client.post(
        "/projects",
        json={
            "workspace_id": workspace["id"],
            "name": "Portable",
            "description": "A portable project",
            "instructions": "Keep it testable.",
        },
        headers=headers,
    ).json()

    file_response = client.post(
        f"/projects/{project['id']}/files",
        json={"path": "src/app.py", "content": "print('hello')"},
        headers=headers,
    )
    assert file_response.status_code == 201
    memory_response = client.post(
        f"/projects/{project['id']}/memories",
        json={"content": "Use Python 3.12."},
        headers=headers,
    )
    assert memory_response.status_code == 201

    exported = client.get(
        f"/projects/{project['id']}/export",
        headers=headers,
    )
    assert exported.status_code == 200
    assert exported.headers["x-project-archive-schema"] == "1"
    assert exported.content.startswith(b"PK")

    imported = parse_project_import(exported.content)
    assert imported.manifest.project["name"] == "Portable"
    assert imported.files == [("src/app.py", "print('hello')")]
    assert imported.memories == ["Use Python 3.12."]


def test_project_archive_rejects_path_traversal():
    payload = _zip_bytes({
        "project.json": json.dumps({
            "schema_version": 1,
            "project": {"name": "Unsafe"},
            "files": [{"path": "../evil.txt", "sha256": "0" * 64, "content_size": 1}],
            "memories": [],
        }).encode(),
        "files/../evil.txt": b"x",
    })
    with pytest.raises(ProjectArchiveError):
        parse_project_import(payload)


def test_project_archive_rejects_checksum_mismatch():
    payload = _zip_bytes({
        "project.json": json.dumps({
            "schema_version": 1,
            "project": {"name": "Mismatch"},
            "files": [{"path": "index.html", "sha256": "0" * 64, "content_size": 1}],
            "memories": [],
        }).encode(),
        "files/index.html": b"x",
    })
    with pytest.raises(ProjectArchiveError):
        parse_project_import(payload)


def test_project_archive_rejects_undeclared_files():
    payload = _zip_bytes({
        "project.json": json.dumps({
            "schema_version": 1,
            "project": {"name": "Extra"},
            "files": [],
            "memories": [],
        }).encode(),
        "files/extra.txt": b"x",
    })
    with pytest.raises(ProjectArchiveError):
        parse_project_import(payload)
