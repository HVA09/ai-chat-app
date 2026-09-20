"""
اختبارات المرحلة السادسة: رفع الملفات وإدارتها
"""
from app.config import settings as app_settings


def _register_and_login(client, email="files@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    return client.cookies.get("access_token")


def test_upload_file_success(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/files/upload", files={"file": ("test.png", b"\x89PNG\r\n\x1a\n" + b"fake", "image/png")}, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "test.png"
    assert body["content_type"] == "image/png"
    assert body["size_bytes"] == len(b"\x89PNG\r\n\x1a\n" + b"fake")


def test_upload_rejects_unsupported_type(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    response = client.post("/files/upload", files={"file": ("virus.exe", b"binary", "application/x-msdownload")}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 415


def test_upload_rejects_oversized_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(app_settings, "MAX_UPLOAD_SIZE_MB", 0)
    token = _register_and_login(client)
    response = client.post("/files/upload", files={"file": ("small.png", b"\x89PNG\r\n\x1a\n" + b"x", "image/png")}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 413


def test_list_files(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/files/upload", files={"file": ("a.pdf", b"%PDF-1.4 pdf-bytes", "application/pdf")}, headers=headers)
    response = client.get("/files", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_download_file_returns_original_bytes(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    upload_response = client.post("/files/upload", files={"file": ("note.csv", b"a,b,c\n1,2,3", "text/csv")}, headers=headers)
    file_id = upload_response.json()["id"]
    download_response = client.get(f"/files/{file_id}", headers=headers)
    assert download_response.status_code == 200
    assert download_response.content == b"a,b,c\n1,2,3"


def test_delete_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    upload_response = client.post("/files/upload", files={"file": ("a.png", b"\x89PNG\r\n\x1a\n" + b"bytes", "image/png")}, headers=headers)
    file_id = upload_response.json()["id"]
    delete_response = client.delete(f"/files/{file_id}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get(f"/files/{file_id}", headers=headers).status_code == 404


def test_cannot_access_other_users_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token_a = _register_and_login(client, "filesowner@example.com")
    upload_response = client.post("/files/upload", files={"file": ("secret.pdf", b"%PDF-1.4 bytes", "application/pdf")}, headers={"Authorization": f"Bearer {token_a}"})
    file_id = upload_response.json()["id"]
    token_b = _register_and_login(client, "filesintruder@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    assert client.get(f"/files/{file_id}", headers=headers_b).status_code == 404
    assert client.delete(f"/files/{file_id}", headers=headers_b).status_code == 404


def test_files_require_authentication(client):
    assert client.get("/files").status_code == 401
    assert client.post("/files/upload", files={"file": ("a.png", b"x", "image/png")}).status_code == 401


def test_workspace_file_is_shared_with_members_but_personal_files_are_not(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))

    token_owner = _register_and_login(client, "workspace-file-owner@example.com")
    from app.models.user import User
    owner = db_session.query(User).filter_by(email="workspace-file-owner@example.com").one()
    workspace = owner.owned_workspaces[0]
    owner_headers = {"Authorization": f"Bearer {token_owner}"}

    upload_response = client.post(
        "/files/upload",
        params={"workspace_id": workspace.id},
        files={"file": ("shared.txt", b"shared knowledge", "text/plain")},
        headers=owner_headers,
    )
    assert upload_response.status_code == 201
    shared_id = upload_response.json()["id"]
    assert upload_response.json()["workspace_id"] == workspace.id
    assert upload_response.json()["is_owner"] is True

    token_member = _register_and_login(client, "workspace-file-member@example.com")
    member = db_session.query(User).filter_by(email="workspace-file-member@example.com").one()
    from app.models.workspace import WorkspaceMember, WorkspaceRole
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=member.id,
            role=WorkspaceRole.member,
        )
    )
    db_session.commit()
    member_headers = {"Authorization": f"Bearer {token_member}"}

    listed = client.get(
        "/files",
        params={"workspace_id": workspace.id},
        headers=member_headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == shared_id
    assert listed.json()[0]["is_owner"] is False
    assert listed.json()[0]["can_delete"] is False

    downloaded = client.get(f"/files/{shared_id}", headers=member_headers)
    assert downloaded.status_code == 200
    assert downloaded.content == b"shared knowledge"

    assert client.delete(f"/files/{shared_id}", headers=member_headers).status_code == 403

    personal = client.post(
        "/files/upload",
        files={"file": ("private.txt", b"private", "text/plain")},
        headers=owner_headers,
    )
    private_id = personal.json()["id"]

    assert client.get(f"/files/{private_id}", headers=member_headers).status_code == 404
    assert client.delete(f"/files/{private_id}", headers=member_headers).status_code == 404


def test_workspace_file_requires_workspace_membership(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token_owner = _register_and_login(client, "workspace-scope-owner@example.com")
    from app.models.user import User
    owner = db_session.query(User).filter_by(email="workspace-scope-owner@example.com").one()
    workspace = owner.owned_workspaces[0]

    token_other = _register_and_login(client, "workspace-scope-other@example.com")
    headers = {"Authorization": f"Bearer {token_other}"}

    response = client.get(
        "/files",
        params={"workspace_id": workspace.id},
        headers=headers,
    )
    assert response.status_code == 404
