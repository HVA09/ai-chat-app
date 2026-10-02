import base64
import io
import zipfile

import pytest

from app.schemas.project_preview import PreviewBuildResponse
from app.models.project_artifact import ProjectArtifact
from app.services import project_preview_artifacts as artifacts


def _build_response(files: dict[str, bytes], entrypoint: str = "dist/index.html") -> PreviewBuildResponse:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, data in files.items():
            archive.writestr(path, data)
    payload = buffer.getvalue()
    return PreviewBuildResponse(
        entrypoint=entrypoint,
        artifact_base64=base64.b64encode(payload).decode("ascii"),
        artifact_size_bytes=len(payload),
    )


def test_preview_token_is_project_and_artifact_scoped(monkeypatch):
    monkeypatch.setattr(artifacts.settings, "JWT_SECRET_KEY", "test-secret")
    token, _ = artifacts.issue_preview_token(10, "artifact", "dist")
    assert artifacts.verify_preview_token(10, "artifact", token) == "dist"

    with pytest.raises(artifacts.PreviewArtifactError):
        artifacts.verify_preview_token(11, "artifact", token)


def test_publish_preview_rejects_zip_path_traversal(monkeypatch):
    monkeypatch.setattr(artifacts, "put_bytes", lambda *args, **kwargs: None)
    build = _build_response({"../index.html": b"<html></html>"})

    with pytest.raises(artifacts.PreviewArtifactError):
        artifacts.publish_preview_artifact(1, build)


def test_publish_preview_stores_only_regular_files(monkeypatch):
    stored = {}

    def fake_put(content, key, content_type):
        stored[key] = (content, content_type)

    monkeypatch.setattr(artifacts, "put_bytes", fake_put)
    monkeypatch.setattr(artifacts.settings, "JWT_SECRET_KEY", "test-secret")
    build = _build_response(
        {
            "dist/index.html": b"<html><script src=\"/assets/app.js\"></script></html>",
            "dist/assets/app.js": b"console.log(1);",
        }
    )

    published = artifacts.publish_preview_artifact(1, build)

    assert published.artifact_id
    assert published.entrypoint == "dist/index.html"
    assert any(key.endswith("/dist/index.html") for key in stored)
    assert any(key.endswith("/dist/assets/app.js") for key in stored)


def test_preview_absolute_urls_are_rewritten_inside_artifact_route():
    html = '<script src="/assets/app.js"></script><link href="https://cdn.example/app.css">'
    rewritten = artifacts.rewrite_absolute_preview_urls(html, 1, "abc", "token", "dist")
    assert "/projects/1/preview-artifacts/abc/token/dist/assets/app.js" in rewritten
    assert "https://cdn.example/app.css" in rewritten


def test_preview_csp_blocks_network_api_access():
    csp = artifacts.preview_csp(["https://frontend.example"])
    assert "sandbox allow-scripts" in csp
    assert "connect-src 'none'" in csp
    assert "frame-ancestors https://frontend.example;" in csp


def test_preview_route_sets_csp_sandbox_without_x_frame_deny(client, db_session, monkeypatch):
    from app.routers import projects as projects_router

    token = _register_and_login(client, "preview-route-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Preview Route"},
        headers=headers,
    ).json()
    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Preview"},
        headers=headers,
    ).json()

    db_session.add(
        ProjectArtifact(
            project_id=project["id"],
            artifact_id="artifact",
            entrypoint="dist/index.html",
            artifact_size_bytes=1,
            expires_at=9999999999,
        )
    )
    db_session.commit()

    monkeypatch.setattr(projects_router, "verify_preview_token", lambda *args, **kwargs: "dist")
    monkeypatch.setattr(
        projects_router,
        "read_preview_file",
        lambda *args, **kwargs: (b"<html><script src=\"/assets/app.js\"></script></html>", "text/html"),
    )

    response = client.get(
        "/projects/1/preview-artifacts/artifact/v1.token/dist/index.html"
    )

    assert response.status_code == 200
    assert "sandbox allow-scripts" in response.headers["content-security-policy"]
    assert "connect-src 'none'" in response.headers["content-security-policy"]
    assert "X-Frame-Options" not in response.headers
    assert "/projects/1/preview-artifacts/artifact/v1.token/dist/assets/app.js" in response.text
