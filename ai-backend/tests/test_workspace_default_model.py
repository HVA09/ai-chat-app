"""اختبارات النموذج الافتراضي لمساحة العمل."""
from unittest.mock import AsyncMock

from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_workspace_default_model_owner_can_set_and_clear(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "AI_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(settings, "AI_ALLOWED_MODELS", ["gemini-2.5-flash", "gemini-test"])

    token = _register_and_login(client, "workspace-model-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    workspace = client.post("/workspaces", json={"name": "Model Policy"}, headers=headers)
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]
    assert workspace.json()["default_ai_model"] is None

    updated = client.patch(
        f"/workspaces/{workspace_id}/model",
        json={"model": "gemini-test"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["default_ai_model"] == "gemini-test"

    cleared = client.patch(
        f"/workspaces/{workspace_id}/model",
        json={"model": None},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["default_ai_model"] is None


def test_workspace_default_model_rejects_invalid_model_and_non_manager(client, db_session, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "AI_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(settings, "AI_ALLOWED_MODELS", ["gemini-2.5-flash", "gemini-test"])

    owner_token = _register_and_login(client, "workspace-model-owner-2@example.com")
    owner = client.get(
        "/users/me", headers={"Authorization": f"Bearer {owner_token}"}
    ).json()

    member_token = _register_and_login(client, "workspace-model-member@example.com")
    member = client.get(
        "/users/me", headers={"Authorization": f"Bearer {member_token}"}
    ).json()

    workspace = Workspace(owner_id=owner["id"], name="Protected")
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

    invalid = client.patch(
        f"/workspaces/{workspace.id}/model",
        json={"model": "not-allowed"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert invalid.status_code == 400

    forbidden = client.patch(
        f"/workspaces/{workspace.id}/model",
        json={"model": "gemini-test"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert forbidden.status_code == 403


def test_chat_uses_workspace_default_model_when_request_does_not_choose_one(
    client, db_session, monkeypatch
):
    from app.config import settings

    monkeypatch.setattr(settings, "AI_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(settings, "AI_ALLOWED_MODELS", ["gemini-2.5-flash", "gemini-test"])
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )

    from app.models.plan import Plan
    from app.models.subscription import Subscription, SubscriptionStatus

    token = _register_and_login(client, "workspace-model-chat@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    owner = client.get("/users/me", headers=headers).json()

    pro_plan = db_session.query(Plan).filter(Plan.name == "Pro").one()
    db_session.add(
        Subscription(
            user_id=owner["id"],
            plan_id=pro_plan.id,
            provider="test",
            provider_subscription_id="workspace-default-model-sub",
            status=SubscriptionStatus.active,
        )
    )
    db_session.flush()

    workspace = Workspace(
        owner_id=owner["id"],
        name="Chat Model",
        default_ai_model="gemini-test",
    )
    db_session.add(workspace)
    db_session.flush()
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=owner["id"],
            role=WorkspaceRole.owner,
        )
    )
    db_session.commit()

    response = client.post(
        "/chat",
        json={"message": "اختبار النموذج", "workspace_id": workspace.id},
        headers=headers,
    )
    assert response.status_code == 200

    from app.models.conversation import Conversation

    conversation = db_session.get(
        Conversation,
        response.json()["conversation_id"],
    )
    assert conversation.ai_model == "gemini-test"
