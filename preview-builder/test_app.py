from fastapi.testclient import TestClient

import app as builder


def test_root_health(monkeypatch):
    monkeypatch.setattr(builder, "ENABLE_BUILDS", True)
    client = TestClient(builder.app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["enabled"] is True


def test_health_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(builder, "ENABLE_BUILDS", False)
    client = TestClient(builder.app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_build_requires_authentication(monkeypatch):
    monkeypatch.setattr(builder, "BUILDER_TOKEN", "secret")
    monkeypatch.setattr(builder, "ENABLE_BUILDS", True)
    client = TestClient(builder.app)

    response = client.post(
        "/v1/build",
        headers={"X-Preview-Protocol": "1"},
        json={
            "project_id": 1,
            "project_kind": "javascript",
            "files": [{"path": "package.json", "content": "{\"name\":\"demo\"}"}],
            "build_command": "npm run build",
        },
    )
    assert response.status_code == 401


def test_build_is_disabled_without_explicit_enable(monkeypatch):
    monkeypatch.setattr(builder, "BUILDER_TOKEN", "secret")
    monkeypatch.setattr(builder, "ENABLE_BUILDS", False)
    client = TestClient(builder.app)

    response = client.post(
        "/v1/build",
        headers={
            "Authorization": "Bearer secret",
            "X-Preview-Protocol": "1",
        },
        json={
            "project_id": 1,
            "project_kind": "javascript",
            "files": [{"path": "package.json", "content": "{\"name\":\"demo\"}"}],
            "build_command": "npm run build",
        },
    )
    assert response.status_code == 503
