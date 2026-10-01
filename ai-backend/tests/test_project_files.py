"""اختبارات ملفات مصدر المشاريع."""
import pytest



def _register_and_login(client, email: str, password: str = "StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def _create_workspace(client, headers, name="Workspace"):
    response = client.post("/workspaces", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_project_file_crud_and_path_safety(client):
    token = _register_and_login(client, "project-files@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers)

    project_response = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "App"},
        headers=headers,
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    created = client.post(
        f"/projects/{project_id}/files",
        json={
            "path": "src/App.jsx",
            "content": "export default function App() { return null; }",
        },
        headers=headers,
    )
    assert created.status_code == 201
    project_file = created.json()
    assert project_file["path"] == "src/App.jsx"
    assert project_file["content"].startswith("export default")

    listed = client.get(
        f"/projects/{project_id}/files",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["path"] == "src/App.jsx"
    assert listed.json()[0]["content_length"] == len(project_file["content"])
    assert "content" not in listed.json()[0]

    detail = client.get(
        f"/projects/{project_id}/files/{project_file['id']}",
        headers=headers,
    )
    assert detail.status_code == 200
    assert detail.json()["content"] == project_file["content"]

    updated = client.patch(
        f"/projects/{project_id}/files/{project_file['id']}",
        json={
            "path": "src/main.jsx",
            "content": "export default function App() { return <main />; }",
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["path"] == "src/main.jsx"

    duplicate = client.post(
        f"/projects/{project_id}/files",
        json={"path": "src/main.jsx", "content": "duplicate"},
        headers=headers,
    )
    assert duplicate.status_code == 409

    from pydantic import ValidationError
    from app.schemas.project_files import ProjectFileCreate

    with pytest.raises(ValidationError):
        ProjectFileCreate(path="../secret.txt", content="nope")

    removed = client.delete(
        f"/projects/{project_id}/files/{project_file['id']}",
        headers=headers,
    )
    assert removed.status_code == 204

    assert client.get(
        f"/projects/{project_id}/files",
        headers=headers,
    ).json() == []


def test_project_files_are_isolated_across_workspaces(client):
    owner_token = _register_and_login(client, "project-file-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    owner_workspace = _create_workspace(client, owner_headers, "Owner")

    other_token = _register_and_login(client, "project-file-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}
    other_workspace = _create_workspace(client, other_headers, "Other")
    project = client.post(
        "/projects",
        json={"workspace_id": other_workspace["id"], "name": "Private"},
        headers=other_headers,
    ).json()

    response = client.get(
        f"/projects/{project['id']}/files",
        headers=owner_headers,
    )
    assert response.status_code == 404

    response = client.post(
        f"/projects/{project['id']}/files",
        json={"path": "secret.txt", "content": "private"},
        headers=owner_headers,
    )
    assert response.status_code == 404

    assert owner_workspace["id"] != other_workspace["id"]
