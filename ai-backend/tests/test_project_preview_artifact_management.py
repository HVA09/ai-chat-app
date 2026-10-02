import base64
import io
import zipfile
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from app.models.project_preview_artifact import ProjectPreviewArtifact
from app.routers import projects as projects_router
from app.schemas.project_preview import PreviewBuildResponse
from app.services.project_preview_artifacts import PublishedPreview
from app.services.project_preview_artifact_registry import register_preview_artifact


def _register_and_login(client, email: str):
    client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass123"},
    )
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert response.status_code == 200
    return client.cookies.get("access_token")


def _build_response(content: bytes) -> PreviewBuildResponse:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("dist/index.html", content)
    payload = buffer.getvalue()
    return PreviewBuildResponse(
        entrypoint="dist/index.html",
        artifact_base64=base64.b64encode(payload).decode("ascii"),
        artifact_size_bytes=len(payload),
    )


def test_preview_artifact_registry_supersedes_previous(db_session, client, monkeypatch):
    token = _register_and_login(client, "artifact-registry@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Artifacts"},
        headers=headers,
    ).json()
    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Registry"},
        headers=headers,
    ).json()

    from app.services import project_preview_artifact_registry as registry

    monkeypatch.setattr(registry, "cleanup_preview_artifact_objects", lambda *args, **kwargs: None)

    first = PublishedPreview(
        artifact_id="artifact-one",
        token="v1.one",
        expires_at=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        entrypoint="dist/index.html",
        file_paths=("dist/index.html",),
        size_bytes=10,
    )
    second = PublishedPreview(
        artifact_id="artifact-two",
        token="v1.two",
        expires_at=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        entrypoint="dist/index.html",
        file_paths=("dist/index.html", "dist/app.js"),
        size_bytes=20,
    )

    register_preview_artifact(
        db_session,
        project["id"],
        first,
        first.size_bytes,
        list(first.file_paths),
    )
    register_preview_artifact(
        db_session,
        project["id"],
        second,
        second.size_bytes,
        list(second.file_paths),
    )

    rows = (
        db_session.query(ProjectPreviewArtifact)
        .filter(ProjectPreviewArtifact.project_id == project["id"])
        .order_by(ProjectPreviewArtifact.artifact_id.asc())
        .all()
    )
    assert [row.artifact_id for row in rows] == ["artifact-one", "artifact-two"]
    assert [row.status for row in rows] == ["superseded", "active"]


def test_preview_artifact_routes_are_managed_and_isolated(client, monkeypatch):
    owner_token = _register_and_login(client, "artifact-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Artifact Owner"},
        headers=owner_headers,
    ).json()
    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Preview History"},
        headers=owner_headers,
    ).json()

    for path, content in (
        ("package.json", '{"name":"demo","scripts":{"build":"vite build"}}'),
        ("src/main.jsx", "export default 1;"),
    ):
        response = client.post(
            f"/projects/{project['id']}/files",
            json={"path": path, "content": content},
            headers=owner_headers,
        )
        assert response.status_code == 201

    first = _build_response(b"<html>one</html>")
    second = _build_response(b"<html>two</html>")
    builder = AsyncMock(side_effect=[first, second])
    monkeypatch.setattr(projects_router, "build_javascript_preview", builder)

    first_response = client.post(
        f"/projects/{project['id']}/preview-build",
        headers=owner_headers,
    )
    assert first_response.status_code == 200
    first_artifact_id = first_response.json()["preview_url"].split("/preview-artifacts/")[1].split("/")[0]

    second_response = client.post(
        f"/projects/{project['id']}/preview-build",
        headers=owner_headers,
    )
    assert second_response.status_code == 200
    second_data = second_response.json()
    second_artifact_id = second_data["preview_url"].split("/preview-artifacts/")[1].split("/")[0]
    assert second_artifact_id != first_artifact_id

    history = client.get(
        f"/projects/{project['id']}/preview-artifacts",
        headers=owner_headers,
    )
    assert history.status_code == 200
    assert len(history.json()) == 2
    assert history.json()[0]["status"] == "active"
    assert history.json()[1]["status"] == "superseded"

    preview_path = second_data["preview_url"].split(f"/projects/{project['id']}/preview-artifacts/", 1)[1]
    preview = client.get(f"/projects/{project['id']}/preview-artifacts/{preview_path}")
    assert preview.status_code == 200

    outsider_token = _register_and_login(client, "artifact-outsider@example.com")
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}
    assert client.get(
        f"/projects/{project['id']}/preview-artifacts",
        headers=outsider_headers,
    ).status_code == 404
    assert client.delete(
        f"/projects/{project['id']}/preview-artifacts/{second_artifact_id}",
        headers=outsider_headers,
    ).status_code == 404

    deleted = client.delete(
        f"/projects/{project['id']}/preview-artifacts/{second_artifact_id}",
        headers=owner_headers,
    )
    assert deleted.status_code == 204
    assert client.get(
        f"/projects/{project['id']}/preview-artifacts",
        headers=owner_headers,
    ).json()[0]["artifact_id"] == first_artifact_id

    revoked = client.get(f"/projects/{project['id']}/preview-artifacts/{preview_path}")
    assert revoked.status_code == 404


def test_preview_artifact_expires_and_is_cleaned(client, db_session, monkeypatch):
    token = _register_and_login(client, "artifact-expiry@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Expiry Workspace"},
        headers=headers,
    ).json()
    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Expiry"},
        headers=headers,
    ).json()

    expired = ProjectPreviewArtifact(
        project_id=project["id"],
        artifact_id="expired-artifact",
        entrypoint="dist/index.html",
        artifact_root="dist",
        size_bytes=10,
        file_count=1,
        files_manifest=["dist/index.html"],
        status="active",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db_session.add(expired)
    db_session.commit()

    cleaned = []
    monkeypatch.setattr(
        projects_router,
        "cleanup_preview_artifact_objects",
        lambda project_id, artifact: cleaned.append((project_id, artifact.artifact_id)),
    )
    response = client.get(
        f"/projects/{project['id']}/preview-artifacts",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()[0]["status"] == "expired"
    assert cleaned == [(project["id"], "expired-artifact")]

    row = db_session.get(ProjectPreviewArtifact, expired.id)
    assert row.status == "expired"
