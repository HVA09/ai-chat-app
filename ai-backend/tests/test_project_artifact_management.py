"""اختبارات إدارة artifacts الخاصة بمعاينة المشاريع."""
import time
from datetime import datetime, timezone, timedelta

from app.models.project_artifact import ProjectArtifact
from app.services import project_preview_artifacts as artifact_service


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


def _create_workspace_project(client, headers):
    workspace = client.post(
        "/workspaces",
        json={"name": "Artifacts"},
        headers=headers,
    ).json()
    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Preview"},
        headers=headers,
    ).json()
    return workspace, project


def _artifact(project_id: int, artifact_id: str, expires_at: int):
    return ProjectArtifact(
        project_id=project_id,
        artifact_id=artifact_id,
        entrypoint="dist/index.html",
        artifact_size_bytes=123,
        expires_at=expires_at,
    )


def test_project_artifacts_are_listed_and_isolated(client, db_session):
    owner_token = _register_and_login(client, "artifact-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    _, project = _create_workspace_project(client, owner_headers)

    other_token = _register_and_login(client, "artifact-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}

    db_session.add(_artifact(project["id"], "a" * 32, int(time.time()) + 900))
    db_session.commit()

    listed = client.get(
        f"/projects/{project['id']}/preview-artifacts",
        headers=owner_headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["artifact_id"] == "a" * 32

    denied = client.get(
        f"/projects/{project['id']}/preview-artifacts",
        headers=other_headers,
    )
    assert denied.status_code == 404


def test_project_artifact_delete_requires_editor_and_invalidates_serving(
    client,
    db_session,
    monkeypatch,
):
    owner_token = _register_and_login(client, "artifact-delete-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace, project = _create_workspace_project(client, owner_headers)

    artifact_id = "b" * 32
    token = "v1.1." + artifact_id + ".token"
    db_session.add(
        _artifact(project["id"], artifact_id, int(time.time()) + 900)
    )
    db_session.commit()

    monkeypatch.setattr(
        artifact_service,
        "delete_prefix",
        lambda prefix: None,
    )

    response = client.delete(
        f"/projects/{project['id']}/preview-artifacts/{artifact_id}",
        headers=owner_headers,
    )
    assert response.status_code == 204

    assert (
        db_session.query(ProjectArtifact)
        .filter(
            ProjectArtifact.project_id == project["id"],
            ProjectArtifact.artifact_id == artifact_id,
        )
        .first()
        is None
    )

    served = client.get(
        f"/projects/{project['id']}/preview-artifacts/{artifact_id}/{token}/dist/index.html"
    )
    assert served.status_code == 404

    workspace_list = client.get(
        f"/projects/{project['id']}/preview-artifacts",
        headers=owner_headers,
    )
    assert workspace_list.status_code == 200
    assert workspace_list.json() == []


def test_project_artifact_cleanup_removes_expired_and_excess_entries(
    client,
    db_session,
    monkeypatch,
):
    owner_token = _register_and_login(client, "artifact-cleanup@example.com")
    headers = {"Authorization": f"Bearer {owner_token}"}
    workspace, project = _create_workspace_project(client, headers)

    now = int(time.time())
    for index in range(6):
        db_session.add(
            _artifact(
                project["id"],
                f"{index + 1:032x}",
                now - 10 if index == 0 else now + 900,
            )
        )
    db_session.commit()

    deleted_prefixes = []
    monkeypatch.setattr(
        artifact_service,
        "delete_prefix",
        lambda prefix: deleted_prefixes.append(prefix),
    )

    response = client.post(
        f"/projects/{project['id']}/preview-artifacts/cleanup",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["removed"] == 2
    assert data["remaining"] == 4
    assert len(deleted_prefixes) == 2
