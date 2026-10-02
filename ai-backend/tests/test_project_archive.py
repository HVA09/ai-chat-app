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


def _login(client, email):
    registered = client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass123"},
    )
    assert registered.status_code == 201
    logged = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert logged.status_code == 200
    return {"Authorization": f"Bearer {logged.json()['access_token']}"}


def _make_archive(name="Imported"):
    content = b"hello"
    manifest = {
        "schema_version": 1,
        "project": {
            "name": name,
            "description": "Imported project",
            "instructions": "Keep tests deterministic.",
        },
        "files": [
            {
                "path": "README.md",
                "sha256": __import__("hashlib").sha256(content).hexdigest(),
                "content_size": len(content),
            }
        ],
        "memories": [{"content": "Remember the archive format."}],
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "project.json",
            json.dumps(manifest, ensure_ascii=False),
        )
        archive.writestr("files/README.md", content)
    return buffer.getvalue()


def test_import_project_resolves_name_conflict_without_overwrite(client):
    headers = _login(client, "archive-import@example.com")
    workspace = client.post(
        "/workspaces",
        json={"name": "Import Workspace"},
        headers=headers,
    ).json()

    created = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Imported"},
        headers=headers,
    )
    assert created.status_code == 201

    archive = _make_archive()
    conflict = client.post(
        "/projects/import",
        data={"workspace_id": str(workspace["id"]), "on_conflict": "fail"},
        files={"archive": ("project.zip", archive, "application/zip")},
        headers=headers,
    )
    assert conflict.status_code == 409

    renamed = client.post(
        "/projects/import",
        data={"workspace_id": str(workspace["id"]), "on_conflict": "rename"},
        files={"archive": ("project.zip", archive, "application/zip")},
        headers=headers,
    )
    assert renamed.status_code == 201
    data = renamed.json()
    assert data["name"] != "Imported"
    assert data["files_imported"] == 1
    assert data["memories_imported"] == 1

    files = client.get(
        f"/projects/{data['project_id']}/files",
        headers=headers,
    )
    assert files.status_code == 200
    assert files.json()[0]["path"] == "README.md"
