from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.schemas.project_preview import PreviewBuildResponse
from app.models.project_artifact import ProjectArtifact


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


def test_project_preview_build_delegates_to_isolated_builder(client, monkeypatch):
    from app.routers import projects as projects_router

    token = _register_and_login(client, "preview-build@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Preview Build"},
        headers=headers,
    ).json()
    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "React App"},
        headers=headers,
    ).json()

    for path, content in (
        ("package.json", '{"name":"demo","scripts":{"build":"vite build"}}'),
        ("src/main.jsx", "export default 1;"),
    ):
        response = client.post(
            f"/projects/{project['id']}/files",
            json={"path": path, "content": content},
            headers=headers,
        )
        assert response.status_code == 201

    mocked = AsyncMock(
        return_value=PreviewBuildResponse(
            entrypoint="dist/index.html",
            artifact_base64="YQ==",
            artifact_size_bytes=1,
        )
    )
    monkeypatch.setattr(projects_router, "build_javascript_preview", mocked)
    monkeypatch.setattr(
        projects_router,
        "publish_preview_artifact",
        lambda project_id, build: SimpleNamespace(
            artifact_id="artifact123",
            token="v1.token",
            expires_at=9999999999,
            entrypoint=build.entrypoint,
        ),
    )

    response = client.post(
        f"/projects/{project['id']}/preview-build",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["entrypoint"] == "dist/index.html"
    assert response.json()["artifact_base64"] == "YQ=="
    assert "/projects/" + str(project["id"]) + "/preview-artifacts/artifact123/v1.token/dist/index.html" in response.json()["preview_url"]
    mocked.assert_awaited_once()
    args = mocked.await_args.args
    assert args[0] == project["id"]
    assert [item.path for item in args[1]] == ["package.json", "src/main.jsx"]

    artifact = db_session.query(ProjectArtifact).filter(
        ProjectArtifact.project_id == project["id"],
        ProjectArtifact.artifact_id == "artifact123",
    ).one()
    assert artifact.entrypoint == "dist/index.html"
    assert artifact.artifact_size_bytes == 1


def test_project_preview_build_remains_workspace_isolated(client, monkeypatch):
    from app.routers import projects as projects_router

    owner_token = _register_and_login(client, "preview-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    owner_workspace = client.post(
        "/workspaces",
        json={"name": "Owner"},
        headers=owner_headers,
    ).json()
    project = client.post(
        "/projects",
        json={"workspace_id": owner_workspace["id"], "name": "Private"},
        headers=owner_headers,
    ).json()

    outsider_token = _register_and_login(client, "preview-outsider@example.com")
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

    mocked = AsyncMock()
    monkeypatch.setattr(projects_router, "build_javascript_preview", mocked)

    response = client.post(
        f"/projects/{project['id']}/preview-build",
        headers=outsider_headers,
    )
    assert response.status_code == 404
    mocked.assert_not_awaited()
