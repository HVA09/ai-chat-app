"""اختبارات إحصاءات استخدام الذكاء الاصطناعي لمساحة العمل."""
from datetime import datetime, timedelta, timezone

from app.models.usage_log import UsageLog
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_workspace_usage_requires_owner_or_admin(client, db_session):
    owner_token = _register_and_login(client, "usage-owner@example.com")
    owner = client.get(
        "/users/me", headers={"Authorization": f"Bearer {owner_token}"}
    ).json()
    member_token = _register_and_login(client, "usage-member@example.com")
    member = client.get(
        "/users/me", headers={"Authorization": f"Bearer {member_token}"}
    ).json()

    workspace = Workspace(owner_id=owner["id"], name="Analytics")
    db_session.add(workspace)
    db_session.flush()
    db_session.add_all(
        [
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=owner["id"],
                role=WorkspaceRole.owner,
            ),
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=member["id"],
                role=WorkspaceRole.member,
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        f"/workspaces/{workspace.id}/usage",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert response.status_code == 403


def test_workspace_usage_aggregates_members_and_ignores_non_members(client, db_session):
    owner_token = _register_and_login(client, "usage-owner-2@example.com")
    owner = client.get(
        "/users/me", headers={"Authorization": f"Bearer {owner_token}"}
    ).json()
    member_token = _register_and_login(client, "usage-member-2@example.com")
    member = client.get(
        "/users/me", headers={"Authorization": f"Bearer {member_token}"}
    ).json()
    outsider_token = _register_and_login(client, "usage-outsider@example.com")
    outsider = client.get(
        "/users/me", headers={"Authorization": f"Bearer {outsider_token}"}
    ).json()

    workspace = Workspace(owner_id=owner["id"], name="Usage Workspace")
    other_workspace = Workspace(owner_id=owner["id"], name="Other Workspace")
    db_session.add_all([workspace, other_workspace])
    db_session.flush()
    db_session.add_all(
        [
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=owner["id"],
                role=WorkspaceRole.owner,
            ),
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=member["id"],
                role=WorkspaceRole.member,
            ),
            WorkspaceMember(
                workspace_id=other_workspace.id,
                user_id=owner["id"],
                role=WorkspaceRole.owner,
            ),
            UsageLog(
                user_id=owner["id"],
                workspace_id=workspace.id,
                endpoint="/chat",
                input_tokens=10,
                output_tokens=20,
                created_at=datetime.now(timezone.utc) - timedelta(hours=1),
            ),
            UsageLog(
                user_id=owner["id"],
                workspace_id=workspace.id,
                endpoint="/chat",
                input_tokens=1,
                output_tokens=2,
                created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            ),
            UsageLog(
                user_id=member["id"],
                workspace_id=workspace.id,
                endpoint="/chat",
                input_tokens=7,
                output_tokens=3,
                created_at=datetime.now(timezone.utc) - timedelta(hours=3),
            ),
            UsageLog(
                user_id=member["id"],
                workspace_id=workspace.id,
                endpoint="/chat",
                input_tokens=100,
                output_tokens=100,
                created_at=datetime.now(timezone.utc) - timedelta(hours=25),
            ),
            UsageLog(
                user_id=owner["id"],
                workspace_id=other_workspace.id,
                endpoint="/chat",
                input_tokens=999,
                output_tokens=999,
                created_at=datetime.now(timezone.utc) - timedelta(hours=1),
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        f"/workspaces/{workspace.id}/usage",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["workspace_id"] == workspace.id
    assert data["window_hours"] == 24
    assert data["used_requests"] == 3
    assert data["input_tokens"] == 18
    assert data["output_tokens"] == 25
    assert data["total_tokens"] == 43

    members = {item["email"]: item for item in data["members"]}
    assert set(members) == {"usage-owner-2@example.com", "usage-member-2@example.com"}
    assert members["usage-owner-2@example.com"]["used_requests"] == 2
    assert members["usage-owner-2@example.com"]["total_tokens"] == 33
    assert members["usage-member-2@example.com"]["used_requests"] == 1
    assert members["usage-member-2@example.com"]["total_tokens"] == 10

    # العضو نفسه موجود في مساحة أخرى، لكن استخدامه هناك لا يظهر في هذه المساحة.
    assert data["total_tokens"] == 43


def test_workspace_usage_csv_requires_manager_and_scopes_workspace(client, db_session):
    owner_token = _register_and_login(client, "usage-csv-owner@example.com")
    owner = client.get(
        "/users/me", headers={"Authorization": f"Bearer {owner_token}"}
    ).json()
    member_token = _register_and_login(client, "usage-csv-member@example.com")
    member = client.get(
        "/users/me", headers={"Authorization": f"Bearer {member_token}"}
    ).json()

    workspace = Workspace(owner_id=owner["id"], name="CSV Workspace")
    other_workspace = Workspace(owner_id=owner["id"], name="CSV Other")
    db_session.add_all([workspace, other_workspace])
    db_session.flush()
    db_session.add_all(
        [
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=owner["id"],
                role=WorkspaceRole.owner,
            ),
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=member["id"],
                role=WorkspaceRole.member,
            ),
            WorkspaceMember(
                workspace_id=other_workspace.id,
                user_id=owner["id"],
                role=WorkspaceRole.owner,
            ),
            UsageLog(
                user_id=owner["id"],
                workspace_id=workspace.id,
                endpoint="/chat",
                input_tokens=10,
                output_tokens=20,
                created_at=datetime.now(timezone.utc) - timedelta(hours=1),
            ),
            UsageLog(
                user_id=member["id"],
                workspace_id=workspace.id,
                endpoint="/chat",
                input_tokens=7,
                output_tokens=3,
                created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            ),
            UsageLog(
                user_id=owner["id"],
                workspace_id=other_workspace.id,
                endpoint="/chat",
                input_tokens=999,
                output_tokens=999,
                created_at=datetime.now(timezone.utc) - timedelta(hours=1),
            ),
        ]
    )
    db_session.commit()

    member_response = client.get(
        f"/workspaces/{workspace.id}/usage.csv",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert member_response.status_code == 403

    owner_response = client.get(
        f"/workspaces/{workspace.id}/usage.csv",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner_response.status_code == 200
    assert "text/csv" in owner_response.headers["content-type"]
    assert f'filename="workspace-{workspace.id}-usage-24h.csv"' in owner_response.headers["content-disposition"]

    body = owner_response.content.decode("utf-8-sig")
    assert "timestamp,user_id,email,full_name,endpoint,input_tokens,output_tokens,total_tokens" in body
    assert "usage-csv-owner@example.com" in body
    assert "usage-csv-member@example.com" in body
    assert "999" not in body
