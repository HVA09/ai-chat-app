"""اختبارات المساعدين المخصصين."""
from unittest.mock import AsyncMock

from app.models import Assistant
from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_assistant_crud(client):
    token = _register_and_login(client, "assistant@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/assistants",
        json={
            "name": "Python Tutor",
            "description": "يساعدني في تعلم بايثون",
            "instructions": "اشرح بالعربية وبخطوات بسيطة، ثم أعطني تمرينًا.",
        },
        headers=headers,
    )
    assert created.status_code == 201
    assistant = created.json()
    assert assistant["name"] == "Python Tutor"

    listed = client.get("/assistants", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == assistant["id"]

    updated = client.patch(
        f"/assistants/{assistant['id']}",
        json={"name": "Python Coach"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Python Coach"

    deleted = client.delete(f"/assistants/{assistant['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/assistants", headers=headers).json() == []


def test_duplicate_assistant_name_rejected_case_insensitively(client):
    token = _register_and_login(client, "assistant-dup@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post(
        "/assistants",
        json={"name": "Tutor", "instructions": "Explain simply."},
        headers=headers,
    ).status_code == 201

    duplicate = client.post(
        "/assistants",
        json={"name": " tutor ", "instructions": "Explain simply."},
        headers=headers,
    )
    assert duplicate.status_code == 409


def test_assistant_is_private_to_owner(client):
    token_a = _register_and_login(client, "assistant-owner@example.com")
    assistant = client.post(
        "/assistants",
        json={"name": "Private", "instructions": "Private instructions."},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()

    token_b = _register_and_login(client, "assistant-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    assert client.get(f"/assistants", headers=headers_b).json() == []
    assert client.patch(
        f"/assistants/{assistant['id']}",
        json={"name": "Hijacked"},
        headers=headers_b,
    ).status_code == 404
    assert client.delete(
        f"/assistants/{assistant['id']}",
        headers=headers_b,
    ).status_code == 404


def test_chat_uses_assistant_instructions(client, monkeypatch):
    mock_reply = AsyncMock(return_value=AIReply(text="رد"))
    monkeypatch.setattr(chat_router_module, "get_ai_reply", mock_reply)

    token = _register_and_login(client, "assistant-chat@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    assistant = client.post(
        "/assistants",
        json={
            "name": "Researcher",
            "instructions": "لخص الإجابة في 3 نقاط.",
        },
        headers=headers,
    ).json()

    response = client.post(
        "/chat",
        json={
            "message": "ما هو لينكس؟",
            "assistant_id": assistant["id"],
        },
        headers=headers,
    )
    assert response.status_code == 200

    sent_message = mock_reply.await_args.args[0]
    assert "[ASSISTANT INSTRUCTIONS]" in sent_message
    assert "لخص الإجابة في 3 نقاط." in sent_message

    conversation_id = response.json()["conversation_id"]
    detail = client.get(f"/conversations/{conversation_id}", headers=headers)
    assert detail.json()["assistant_id"] == assistant["id"]


def test_assistant_version_history_and_restore(client):
    token = _register_and_login(client, "assistant-versions@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/assistants",
        json={
            "name": "Tutor",
            "description": "Original",
            "instructions": "اشرح بالعربية.",
        },
        headers=headers,
    )
    assert created.status_code == 201
    assistant = created.json()

    versions = client.get(
        f"/assistants/{assistant['id']}/versions",
        headers=headers,
    )
    assert versions.status_code == 200
    assert len(versions.json()) == 1
    assert versions.json()[0]["version"] == 1
    assert versions.json()[0]["instructions"] == "اشرح بالعربية."
    assert versions.json()[0]["knowledge_file_ids"] == []
    assert versions.json()[0]["tool_policy_snapshot"]["allowed_tools"]

    updated = client.patch(
        f"/assistants/{assistant['id']}",
        json={"instructions": "اشرح بالإنجليزية وبأمثلة عملية."},
        headers=headers,
    )
    assert updated.status_code == 200

    versions = client.get(
        f"/assistants/{assistant['id']}/versions",
        headers=headers,
    )
    assert [item["version"] for item in versions.json()] == [2, 1]

    restored = client.post(
        f"/assistants/{assistant['id']}/versions/1/restore",
        headers=headers,
    )
    assert restored.status_code == 200
    assert restored.json()["instructions"] == "اشرح بالعربية."

    versions = client.get(
        f"/assistants/{assistant['id']}/versions",
        headers=headers,
    )
    assert [item["version"] for item in versions.json()] == [3, 2, 1]
    assert versions.json()[0]["instructions"] == "اشرح بالعربية."


def test_assistant_version_compare_current(client):
    token = _register_and_login(client, "assistant-version-compare@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    assistant = client.post(
        "/assistants",
        json={
            "name": "Tutor",
            "description": "Original",
            "instructions": "اشرح بالعربية.",
        },
        headers=headers,
    ).json()

    client.patch(
        f"/assistants/{assistant['id']}",
        json={
            "name": "Tutor Updated",
            "description": "Updated",
            "instructions": "اشرح بالإنجليزية وبأمثلة.",
        },
        headers=headers,
    )

    response = client.get(
        f"/assistants/{assistant['id']}/versions/1/compare-current",
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["from_version"] == 1
    assert payload["changed"] is True
    assert "-name: Tutor" in payload["diff"]
    assert "+name: Tutor Updated" in payload["diff"]
    assert "-اشرح بالعربية." in payload["diff"]
    assert "+اشرح بالإنجليزية وبأمثلة." in payload["diff"]

    assert client.get(
        f"/assistants/{assistant['id']}/versions/999/compare-current",
        headers=headers,
    ).status_code == 404


def test_assistant_versions_are_private_to_owner(client):
    token_a = _register_and_login(client, "assistant-version-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    assistant = client.post(
        "/assistants",
        json={"name": "Private", "instructions": "Secret instructions."},
        headers=headers_a,
    ).json()

    token_b = _register_and_login(client, "assistant-version-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    assert client.get(
        f"/assistants/{assistant['id']}/versions",
        headers=headers_b,
    ).status_code == 404
    assert client.post(
        f"/assistants/{assistant['id']}/versions/1/restore",
        headers=headers_b,
    ).status_code == 404


def test_assistant_usage_analytics(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "assistant-analytics@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    assistant = client.post(
        "/assistants",
        json={
            "name": "Analytics Tutor",
            "instructions": "اشرح بإيجاز.",
        },
        headers=headers,
    ).json()

    first = client.post(
        "/chat",
        json={"message": "رسالة 1", "assistant_id": assistant["id"]},
        headers=headers,
    )
    assert first.status_code == 200

    second = client.post(
        "/chat",
        json={
            "message": "رسالة 2",
            "conversation_id": first.json()["conversation_id"],
            "assistant_id": assistant["id"],
        },
        headers=headers,
    )
    assert second.status_code == 200

    analytics = client.get(
        f"/assistants/{assistant['id']}/analytics",
        params={"days": 30},
        headers=headers,
    )
    assert analytics.status_code == 200
    payload = analytics.json()
    assert payload["assistant_id"] == assistant["id"]
    assert payload["days"] == 30
    assert payload["conversation_count"] == 1
    assert payload["message_count"] == 4
    assert payload["active_user_count"] == 1
    assert payload["last_used_at"] is not None


def test_assistant_usage_analytics_is_private_to_owner(client):
    token_a = _register_and_login(client, "assistant-analytics-owner@example.com")
    assistant = client.post(
        "/assistants",
        json={"name": "Private Analytics", "instructions": "خاص"},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()

    token_b = _register_and_login(client, "assistant-analytics-other@example.com")
    response = client.get(
        f"/assistants/{assistant['id']}/analytics",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_assistant_snapshot_update_locks_shared_workspaces_first(
    client, db_session, monkeypatch
):
    from app.models.assistant_workspace_share import AssistantWorkspaceShare
    from app.routers import assistants as assistants_router_module

    token = _register_and_login(client, "assistant-snapshot-lock@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assistant = client.post(
        "/assistants",
        json={"name": "Lock-aware assistant", "instructions": "Initial"},
        headers=headers,
    ).json()
    workspace = client.post(
        "/workspaces",
        json={"name": "Snapshot lock workspace"},
        headers=headers,
    ).json()
    owner = db_session.query(Assistant).filter(
        Assistant.id == assistant["id"]
    ).one()
    db_session.add(
        AssistantWorkspaceShare(
            assistant_id=owner.id,
            workspace_id=workspace["id"],
            shared_by_user_id=owner.user_id,
        )
    )
    db_session.commit()

    locked = []
    original_lock = assistants_router_module.lock_workspaces_for_update

    def capture_lock(db, workspace_ids):
        locked.extend(workspace_ids)
        return original_lock(db, workspace_ids)

    monkeypatch.setattr(
        assistants_router_module, "lock_workspaces_for_update", capture_lock
    )
    updated = client.patch(
        f"/assistants/{assistant['id']}",
        json={"instructions": "Updated after acquiring lock context"},
        headers=headers,
    )

    assert updated.status_code == 200
    assert locked == [workspace["id"]]


def test_retention_locks_only_snapshots_referencing_target_files_on_postgres(db_session):
    """Unrelated assistant history must remain unlocked during file retention."""
    from uuid import uuid4

    import pytest
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import sessionmaker

    from app.models.assistant_file_link import AssistantFileLink
    from app.models.assistant_version import AssistantVersion
    from app.models.file_attachment import FileAttachment
    from app.models.user import User
    from app.services import project_file_retention

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock behavior is required for this regression test")

    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    setup = session_factory()
    user = User(
        email=f"retention-filter-{suffix}@example.test",
        hashed_password="test-only-hash",
    )
    setup.add(user)
    setup.flush()
    target_assistant = Assistant(
        user_id=user.id,
        name=f"Target {suffix[:10]}",
        instructions="Target assistant.",
    )
    unrelated_assistant = Assistant(
        user_id=user.id,
        name=f"Unrelated {suffix[:10]}",
        instructions="Unrelated assistant.",
    )
    setup.add_all([target_assistant, unrelated_assistant])
    setup.flush()
    attachment = FileAttachment(
        user_id=user.id,
        original_filename="target.txt",
        stored_filename=f"target-{suffix}.txt",
        object_key=f"users/{user.id}/target-{suffix}.txt",
        content_type="text/plain",
        size_bytes=1,
        extracted_text="x",
    )
    setup.add(attachment)
    setup.flush()
    target_version = AssistantVersion(
        assistant_id=target_assistant.id,
        version=1,
        name=target_assistant.name,
        instructions=target_assistant.instructions,
        knowledge_file_ids=[attachment.id],
        tool_policy_snapshot={},
    )
    unrelated_version = AssistantVersion(
        assistant_id=unrelated_assistant.id,
        version=1,
        name=unrelated_assistant.name,
        instructions=unrelated_assistant.instructions,
        knowledge_file_ids=[999999999],
        tool_policy_snapshot={},
    )
    setup.add_all([target_version, unrelated_version])
    setup.add(AssistantFileLink(
        assistant_id=target_assistant.id,
        file_id=attachment.id,
    ))
    setup.commit()
    user_id = user.id
    target_version_id = target_version.id
    unrelated_version_id = unrelated_version.id
    file_id = attachment.id
    setup.close()

    retention = session_factory()
    probe = session_factory()
    try:
        retention.begin()
        project_file_retention._privatize_attachment_ids(retention, [file_id])

        # NOWAIT succeeds only if the unrelated historical row was not locked.
        try:
            probe.execute(
                text(
                    "SELECT id FROM assistant_versions "
                    "WHERE id = :version_id FOR UPDATE NOWAIT"
                ),
                {"version_id": unrelated_version_id},
            ).one()
        except OperationalError as exc:
            pytest.fail(f"unrelated assistant snapshot was locked: {exc}")

        target = retention.query(AssistantVersion).filter(
            AssistantVersion.id == target_version_id
        ).one()
        assert target.knowledge_file_ids == []
        unrelated = probe.query(AssistantVersion).filter(
            AssistantVersion.id == unrelated_version_id
        ).one()
        assert unrelated.knowledge_file_ids == [999999999]
    finally:
        if retention.in_transaction():
            retention.rollback()
        if probe.in_transaction():
            probe.rollback()
        retention.close()
        probe.close()
        with session_factory() as cleanup:
            cleanup.query(User).filter(User.id == user_id).delete()
            cleanup.commit()


def test_retention_serializes_with_assistant_snapshot_creation_on_postgres(db_session):
    """A snapshot writer must see scrubbed links after retention owns the assistant row."""
    from threading import Event, Thread
    from time import monotonic, sleep
    from uuid import uuid4

    import pytest
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from app.models.assistant_file_link import AssistantFileLink
    from app.models.assistant_version import AssistantVersion
    from app.models.file_attachment import FileAttachment
    from app.models.user import User
    from app.routers import assistants as assistants_router_module
    from app.services import project_file_retention

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock behavior is required for this regression test")

    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    creator = session_factory()
    user = User(
        email=f"snapshot-retention-{suffix}@example.test",
        hashed_password="test-only-hash",
    )
    creator.add(user)
    creator.flush()
    assistant = Assistant(
        user_id=user.id,
        name=f"Snapshot {suffix[:12]}",
        instructions="Test snapshot serialization.",
    )
    creator.add(assistant)
    creator.flush()
    attachment = FileAttachment(
        user_id=user.id,
        original_filename="retention-race.txt",
        stored_filename=f"retention-race-{suffix}.txt",
        object_key=f"users/{user.id}/retention-race-{suffix}.txt",
        content_type="text/plain",
        size_bytes=10,
        extracted_text="private test content",
    )
    creator.add(attachment)
    creator.flush()
    creator.add(
        AssistantFileLink(assistant_id=assistant.id, file_id=attachment.id)
    )
    creator.add(
        AssistantVersion(
            assistant_id=assistant.id,
            version=1,
            name=assistant.name,
            instructions=assistant.instructions,
            knowledge_file_ids=[attachment.id],
            tool_policy_snapshot={},
        )
    )
    creator.commit()
    user_id, assistant_id, file_id = user.id, assistant.id, attachment.id
    creator.close()

    retention = session_factory()
    writer_started = Event()
    writer_finished = Event()
    writer_pid = {}
    writer_errors = []

    def create_snapshot_after_retention():
        try:
            with session_factory() as writer:
                writer.begin()
                writer_pid["value"] = writer.execute(
                    text("SELECT pg_backend_pid()")
                ).scalar_one()
                writer_started.set()
                current_assistant = writer.query(Assistant).filter(
                    Assistant.id == assistant_id
                ).one()
                assistants_router_module._lock_assistant_version_context(
                    current_assistant, writer
                )
                assistants_router_module._create_assistant_version(
                    current_assistant, writer
                )
                writer.commit()
        except BaseException as exc:
            writer_errors.append(exc)
        finally:
            writer_finished.set()

    thread = Thread(target=create_snapshot_after_retention, daemon=True)
    try:
        retention.begin()
        project_file_retention._privatize_attachment_ids(retention, [file_id])
        thread.start()
        assert writer_started.wait(5), "snapshot writer did not start"

        deadline = monotonic() + 5
        waiting_on_lock = False
        while monotonic() < deadline:
            with session_factory() as probe:
                wait_type = probe.execute(
                    text(
                        "SELECT wait_event_type FROM pg_stat_activity "
                        "WHERE pid = :pid"
                    ),
                    {"pid": writer_pid["value"]},
                ).scalar_one_or_none()
            if wait_type == "Lock":
                waiting_on_lock = True
                break
            sleep(0.01)

        assert waiting_on_lock, "snapshot writer did not wait for retention's assistant lock"
        assert not writer_finished.is_set()
        retention.commit()
        assert writer_finished.wait(5), "snapshot writer did not finish after retention commit"
        thread.join(timeout=5)
        assert not thread.is_alive()
        assert writer_errors == []
    finally:
        if retention.in_transaction():
            retention.rollback()
        if thread.ident is not None:
            thread.join(timeout=5)
        retention.close()
        try:
            with session_factory() as verify:
                versions = (
                    verify.query(AssistantVersion)
                    .filter(AssistantVersion.assistant_id == assistant_id)
                    .order_by(AssistantVersion.version.asc())
                    .all()
                )
                assert [item.version for item in versions] == [1, 2]
                assert versions[0].knowledge_file_ids == []
                assert versions[1].knowledge_file_ids == []
                assert verify.query(AssistantFileLink).filter(
                    AssistantFileLink.file_id == file_id
                ).count() == 0
        finally:
            with session_factory() as cleanup:
                cleanup.query(User).filter(User.id == user_id).delete()
                cleanup.commit()


def test_restore_revalidates_snapshot_after_project_file_retention_on_postgres(
    db_session,
):
    """A route-level restore must not resurrect a file scrubbed by retention."""
    from threading import Event, Thread
    from time import monotonic, sleep
    from uuid import uuid4

    import pytest
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from app.models.assistant_file_link import AssistantFileLink
    from app.models.assistant_version import AssistantVersion
    from app.models.assistant_workspace_share import AssistantWorkspaceShare
    from app.models.file_attachment import FileAttachment
    from app.models.user import User
    from app.models.workspace import Workspace
    from app.routers.assistants import restore_assistant_version
    from app.services.project_file_retention import _privatize_attachment_ids

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock behavior is required for this regression test")

    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    creator = session_factory()
    user = User(
        email=f"restore-retention-{suffix}@example.test",
        hashed_password="test-only-hash",
    )
    creator.add(user)
    creator.flush()
    workspace = Workspace(owner_id=user.id, name=f"Restore retention {suffix[:12]}")
    creator.add(workspace)
    creator.flush()
    assistant = Assistant(
        user_id=user.id,
        name=f"Restore {suffix[:12]}",
        instructions="Original instructions.",
    )
    creator.add(assistant)
    creator.flush()
    attachment = FileAttachment(
        user_id=user.id,
        workspace_id=workspace.id,
        original_filename="restore-race.txt",
        stored_filename=f"restore-race-{suffix}.txt",
        object_key=f"users/{user.id}/restore-race-{suffix}.txt",
        content_type="text/plain",
        size_bytes=12,
        extracted_text="private restore race",
    )
    creator.add(attachment)
    creator.flush()
    creator.add(
        AssistantWorkspaceShare(
            assistant_id=assistant.id,
            workspace_id=workspace.id,
            shared_by_user_id=user.id,
        )
    )
    creator.add(AssistantFileLink(assistant_id=assistant.id, file_id=attachment.id))
    creator.add(
        AssistantVersion(
            assistant_id=assistant.id,
            version=1,
            name=assistant.name,
            instructions=assistant.instructions,
            knowledge_file_ids=[attachment.id],
            tool_policy_snapshot={},
        )
    )
    creator.commit()
    user_id, workspace_id = user.id, workspace.id
    assistant_id, file_id = assistant.id, attachment.id
    creator.close()

    retention = session_factory()
    restore_started = Event()
    restore_finished = Event()
    restore_pid = {}
    restore_errors = []

    def restore_after_retention():
        try:
            with session_factory() as restore_db:
                restore_db.begin()
                restore_pid["value"] = restore_db.execute(
                    text("SELECT pg_backend_pid()")
                ).scalar_one()
                current_user = restore_db.get(User, user_id)
                restore_started.set()
                restore_assistant_version(
                    assistant_id,
                    1,
                    current_user,
                    restore_db,
                )
        except BaseException as exc:
            restore_errors.append(exc)
        finally:
            restore_finished.set()

    thread = Thread(target=restore_after_retention, daemon=True)
    try:
        retention.begin()
        retention.query(Workspace.id).filter(
            Workspace.id == workspace_id
        ).with_for_update().one()
        _privatize_attachment_ids(retention, [file_id])

        thread.start()
        assert restore_started.wait(5), "restore route did not start"

        deadline = monotonic() + 5
        waiting_on_lock = False
        while monotonic() < deadline:
            with session_factory() as probe:
                wait_type = probe.execute(
                    text(
                        "SELECT wait_event_type FROM pg_stat_activity "
                        "WHERE pid = :pid"
                    ),
                    {"pid": restore_pid["value"]},
                ).scalar_one_or_none()
            if wait_type == "Lock":
                waiting_on_lock = True
                break
            sleep(0.01)

        assert waiting_on_lock, "restore route did not wait for retention's workspace lock"
        assert not restore_finished.is_set()
        retention.commit()
        assert restore_finished.wait(5), "restore route did not finish after retention commit"
        thread.join(timeout=5)
        assert not thread.is_alive()
        assert restore_errors == []
    finally:
        if retention.in_transaction():
            retention.rollback()
        if thread.ident is not None:
            thread.join(timeout=5)
        retention.close()
        try:
            with session_factory() as verify:
                snapshot = verify.query(AssistantVersion).filter(
                    AssistantVersion.assistant_id == assistant_id,
                    AssistantVersion.version == 1,
                ).one()
                assert snapshot.knowledge_file_ids == []
                assert verify.query(AssistantFileLink).filter(
                    AssistantFileLink.assistant_id == assistant_id,
                    AssistantFileLink.file_id == file_id,
                ).count() == 0
                restored_versions = verify.query(AssistantVersion).filter(
                    AssistantVersion.assistant_id == assistant_id
                ).order_by(AssistantVersion.version.asc()).all()
                assert [item.version for item in restored_versions] == [1, 2]
                assert restored_versions[1].knowledge_file_ids == []
        finally:
            with session_factory() as cleanup:
                cleanup.query(User).filter(User.id == user_id).delete()
                cleanup.commit()



def test_retention_locks_assistant_with_only_historical_file_reference_on_postgres(
    db_session,
):
    """A historical snapshot without a live file link still requires its assistant lock."""
    from uuid import uuid4

    import pytest
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import sessionmaker

    from app.models.assistant_version import AssistantVersion
    from app.models.file_attachment import FileAttachment
    from app.models.user import User
    from app.services import project_file_retention

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock behavior is required for this regression test")

    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    setup = session_factory()
    user = User(
        email=f"retention-historical-only-{suffix}@example.test",
        hashed_password="test-only-hash",
    )
    setup.add(user)
    setup.flush()
    assistant = Assistant(
        user_id=user.id,
        name=f"Historical only {suffix[:10]}",
        instructions="No current file link.",
    )
    setup.add(assistant)
    setup.flush()
    attachment = FileAttachment(
        user_id=user.id,
        original_filename="historical-only.txt",
        stored_filename=f"historical-only-{suffix}.txt",
        object_key=f"users/{user.id}/historical-only-{suffix}.txt",
        content_type="text/plain",
        size_bytes=1,
        extracted_text="x",
    )
    setup.add(attachment)
    setup.flush()
    version = AssistantVersion(
        assistant_id=assistant.id,
        version=1,
        name=assistant.name,
        instructions=assistant.instructions,
        knowledge_file_ids=[attachment.id],
        tool_policy_snapshot={},
    )
    setup.add(version)
    setup.commit()
    user_id, assistant_id = user.id, assistant.id
    version_id, file_id = version.id, attachment.id
    setup.close()

    retention = session_factory()
    probe = session_factory()
    try:
        retention.begin()
        project_file_retention._privatize_attachment_ids(retention, [file_id])

        # The assistant must be locked even though no live AssistantFileLink
        # exists; otherwise a concurrent restore can race the historical scrub.
        try:
            probe.execute(
                text("SELECT id FROM assistants WHERE id = :assistant_id FOR UPDATE NOWAIT"),
                {"assistant_id": assistant_id},
            ).one()
        except OperationalError:
            pass
        else:
            pytest.fail("assistant with a historical file reference was not locked")

        scrubbed = retention.query(AssistantVersion).filter(
            AssistantVersion.id == version_id
        ).one()
        assert scrubbed.knowledge_file_ids == []
    finally:
        if retention.in_transaction():
            retention.rollback()
        if probe.in_transaction():
            probe.rollback()
        retention.close()
        probe.close()
        with session_factory() as cleanup:
            cleanup.query(User).filter(User.id == user_id).delete()
            cleanup.commit()
