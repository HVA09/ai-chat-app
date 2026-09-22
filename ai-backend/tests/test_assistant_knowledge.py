"""اختبارات ملفات المعرفة الخاصة بالمساعدين."""
import asyncio
from unittest.mock import AsyncMock

from app.models.assistant import Assistant
from app.models.assistant_file_link import AssistantFileLink
from app.models.conversation import Conversation
from app.models.file_attachment import FileAttachment
from app.models.file_chunk import FileChunk
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.services import rag


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


def test_assistant_knowledge_attach_list_and_detach(client, db_session):
    token = _register_and_login(client, "assistant-knowledge@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    assistant = client.post(
        "/assistants",
        json={
            "name": "Linux Tutor",
            "description": "Linux assistant",
            "instructions": "Explain Linux clearly.",
        },
        headers=headers,
    )
    assert assistant.status_code == 201
    assistant_id = assistant.json()["id"]

    user = db_session.query(User).filter(User.email == "assistant-knowledge@example.com").one()
    file = FileAttachment(
        user_id=user.id,
        original_filename="linux.txt",
        stored_filename="linux.txt",
        content_type="text/plain",
        size_bytes=20,
        extracted_text="Linux notes",
    )
    db_session.add(file)
    db_session.commit()

    attached = client.post(
        f"/assistants/{assistant_id}/files/{file.id}",
        headers=headers,
    )
    assert attached.status_code == 200
    assert attached.json()["is_attached"] is True

    listed = client.get(f"/assistants/{assistant_id}/files", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [file.id]

    detached = client.delete(
        f"/assistants/{assistant_id}/files/{file.id}",
        headers=headers,
    )
    assert detached.status_code == 204
    assert client.get(f"/assistants/{assistant_id}/files", headers=headers).json() == []


def test_assistant_cannot_attach_workspace_or_project_file(client, db_session):
    token = _register_and_login(client, "assistant-knowledge-scope@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    assistant = client.post(
        "/assistants",
        json={
            "name": "Private Tutor",
            "instructions": "Use the files.",
        },
        headers=headers,
    ).json()

    user = db_session.query(User).filter(
        User.email == "assistant-knowledge-scope@example.com"
    ).one()
    workspace = Workspace(owner_id=user.id, name="Research")
    db_session.add(workspace)
    db_session.flush()
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role=WorkspaceRole.owner,
        )
    )
    db_session.flush()

    file = FileAttachment(
        user_id=user.id,
        workspace_id=workspace.id,
        original_filename="workspace.txt",
        stored_filename="workspace.txt",
        content_type="text/plain",
        size_bytes=20,
        extracted_text="Workspace notes",
    )
    db_session.add(file)
    db_session.commit()

    response = client.post(
        f"/assistants/{assistant['id']}/files/{file.id}",
        headers=headers,
    )
    assert response.status_code == 404


def test_other_user_cannot_manage_assistant_knowledge(client, db_session):
    token_a = _register_and_login(client, "assistant-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    assistant = client.post(
        "/assistants",
        json={"name": "Owner Assistant", "instructions": "Private"},
        headers=headers_a,
    ).json()

    user_a = db_session.query(User).filter(User.email == "assistant-owner@example.com").one()
    file = FileAttachment(
        user_id=user_a.id,
        original_filename="owner.txt",
        stored_filename="owner.txt",
        content_type="text/plain",
        size_bytes=20,
        extracted_text="Owner secret knowledge",
    )
    db_session.add(file)
    db_session.commit()

    token_b = _register_and_login(client, "assistant-attacker@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    assert client.post(
        f"/assistants/{assistant['id']}/files/{file.id}",
        headers=headers_b,
    ).status_code == 404
    assert client.get(
        f"/assistants/{assistant['id']}/files",
        headers=headers_b,
    ).status_code == 404


def test_assistant_knowledge_is_retrieved_for_shared_conversation(db_session, monkeypatch):
    owner = User(email="assistant-rag-owner@example.com", hashed_password="hashed")
    member = User(email="assistant-rag-member@example.com", hashed_password="hashed")
    db_session.add_all([owner, member])
    db_session.flush()

    workspace = Workspace(owner_id=owner.id, name="Shared")
    db_session.add(workspace)
    db_session.flush()
    db_session.add_all(
        [
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=owner.id,
                role=WorkspaceRole.owner,
            ),
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=member.id,
                role=WorkspaceRole.member,
            ),
        ]
    )

    assistant = Assistant(
        user_id=owner.id,
        name="Research Assistant",
        instructions="Use the knowledge files.",
    )
    db_session.add(assistant)
    db_session.flush()

    conversation = Conversation(
        user_id=member.id,
        workspace_id=workspace.id,
        assistant_id=assistant.id,
        title="Shared chat",
    )
    db_session.add(conversation)
    db_session.flush()

    file = FileAttachment(
        user_id=owner.id,
        original_filename="research.txt",
        stored_filename="research.txt",
        content_type="text/plain",
        size_bytes=50,
        extracted_text="Research knowledge",
    )
    db_session.add(file)
    db_session.flush()
    db_session.add(
        FileChunk(
            file_id=file.id,
            chunk_index=0,
            content="Shared assistant knowledge evidence",
            embedding=[0.1] * 768,
        )
    )
    db_session.add(
        AssistantFileLink(
            assistant_id=assistant.id,
            file_id=file.id,
        )
    )
    db_session.commit()

    async def fake_embed_query(_query):
        return [0.1] * 768

    monkeypatch.setattr(rag, "embed_query", fake_embed_query)

    rows = asyncio.run(
        rag.retrieve_relevant_chunks(
            db_session,
            member.id,
            conversation.id,
            "evidence",
            workspace_id=workspace.id,
            assistant_id=assistant.id,
        )
    )

    assert len(rows) == 1
    assert rows[0][1].id == file.id
    assert rows[0][0].content == "Shared assistant knowledge evidence"


def test_assistant_knowledge_does_not_cross_assistants(db_session, monkeypatch):
    owner = User(email="assistant-rag-isolation@example.com", hashed_password="hashed")
    db_session.add(owner)
    db_session.flush()

    workspace = Workspace(owner_id=owner.id, name="Isolation")
    db_session.add(workspace)
    db_session.flush()
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=owner.id,
            role=WorkspaceRole.owner,
        )
    )

    assistant_a = Assistant(
        user_id=owner.id,
        name="A",
        instructions="A",
    )
    assistant_b = Assistant(
        user_id=owner.id,
        name="B",
        instructions="B",
    )
    db_session.add_all([assistant_a, assistant_b])
    db_session.flush()

    conversation = Conversation(
        user_id=owner.id,
        workspace_id=workspace.id,
        assistant_id=assistant_b.id,
        title="B chat",
    )
    db_session.add(conversation)
    db_session.flush()

    file = FileAttachment(
        user_id=owner.id,
        original_filename="a.txt",
        stored_filename="a.txt",
        content_type="text/plain",
        size_bytes=10,
        extracted_text="A knowledge",
    )
    db_session.add(file)
    db_session.flush()
    db_session.add(
        FileChunk(
            file_id=file.id,
            chunk_index=0,
            content="Only assistant A",
            embedding=[0.1] * 768,
        )
    )
    db_session.add(
        AssistantFileLink(
            assistant_id=assistant_a.id,
            file_id=file.id,
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        rag,
        "embed_query",
        AsyncMock(return_value=[0.1] * 768),
    )

    rows = asyncio.run(
        rag.retrieve_relevant_chunks(
            db_session,
            owner.id,
            conversation.id,
            "knowledge",
            workspace_id=workspace.id,
            assistant_id=assistant_b.id,
        )
    )
    assert rows == []
