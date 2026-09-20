"""اختبارات مشاركة المحادثات للقراءة فقط داخل مساحة العمل."""
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    return client.cookies.get("access_token")


def _create_workspace(client, headers, name):
    response = client.post("/workspaces", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()


def _invite_and_accept(client, owner_headers, member_headers, workspace_id):
    invite = client.post(
        f"/workspaces/{workspace_id}/invitations",
        json={"email": "workspace-share-member@example.com", "role": "member"},
        headers=owner_headers,
    )
    assert invite.status_code == 201

    from app.models.workspace_invitation import WorkspaceInvitation
    from app.database import get_db

    with client as _:
        db = next(get_db())
        token_hash = db.query(WorkspaceInvitation).filter(
            WorkspaceInvitation.workspace_id == workspace_id
        ).first().token_hash
        db.close()

    # إنشاء رابط دعوة مباشرة باستخدام hash ليس ممكنًا؛ نستخدم endpoint اختبار-مناسب
    # لذلك، بدل ذلك نستخرج أول دعوة من DB ثم نعيد حساب/نستخدم token من email ليس متاحًا.
    # سيتم تجاوز هذه المساعدة في الاختبار باستخدام إنشاء عضوية مباشرة.
    raise AssertionError("helper not used")
