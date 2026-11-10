"""End-to-end QueuePool acceptance for the non-Agent SSE route.

This test is intentionally restricted to the local PostgreSQL service configured
by GitHub Actions. It must never connect to Supabase, Render, or another remote DB.
"""
import asyncio
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.models.conversation import Conversation, Message
from app.models.usage_log import UsageLog
from app.models.user import User, UserRole
from app.models.workspace import Workspace
from app.routers import chat as chat_router_module


def test_chat_stream_releases_single_postgres_pool_slot_during_blocked_provider_wait(
    monkeypatch,
):
    """A second request must acquire the only PostgreSQL slot while SSE awaits AI."""
    database_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/ai_backend_test",
    )
    parsed_url = make_url(database_url)
    if (
        parsed_url.drivername.split("+", 1)[0] != "postgresql"
        or parsed_url.host not in {"localhost", "127.0.0.1"}
        or parsed_url.port != 5432
        or parsed_url.database != "ai_backend_test"
        or bool(parsed_url.query)
    ):
        pytest.skip(
            "SSE Pool acceptance only runs against localhost:5432/ai_backend_test "
            "without connection-routing overrides; remote and production databases "
            "are forbidden"
        )

    pool_engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=1,
        max_overflow=0,
        pool_timeout=1,
        pool_pre_ping=True,
    )
    PoolSession = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=pool_engine,
        expire_on_commit=True,
    )
    db = PoolSession()
    suffix = uuid4().hex
    user_id = None
    workspace_id = None
    conversation_id = None

    try:
        # The normal CI fixture has already created the migrated test schema.
        # create_all is deliberately not called here to avoid schema mutation.
        user = User(
            email=f"sse-pool-acceptance-{suffix}@example.invalid",
            hashed_password="not-a-real-password",
            role=UserRole.user,
        )
        db.add(user)
        db.flush()
        user_id = user.id

        workspace = Workspace(
            owner_id=user.id,
            name=f"sse-pool-acceptance-{suffix[:12]}",
        )
        db.add(workspace)
        db.flush()
        workspace_id = workspace.id

        conversation = Conversation(
            user_id=user.id,
            workspace_id=workspace.id,
            title="QueuePool acceptance",
            ai_model="pool-acceptance-model",
        )
        db.add(conversation)
        db.commit()
        conversation_id = conversation.id

        # Reload a persistent ORM row while the one-connection pool is checked out.
        conversation = db.query(Conversation).filter_by(id=conversation_id).one()
        assert db.expire_on_commit is True
        assert pool_engine.pool.checkedout() == 1

        monkeypatch.setattr(
            chat_router_module,
            "_get_or_create_conversation",
            lambda *_args, **_kwargs: conversation,
        )
        monkeypatch.setattr(
            chat_router_module,
            "_attach_requested_files",
            lambda *_args, **_kwargs: None,
        )
        monkeypatch.setattr(
            chat_router_module,
            "enforce_workspace_daily_ai_limit",
            lambda *_args, **_kwargs: None,
        )
        monkeypatch.setattr(
            chat_router_module,
            "extract_agent_request",
            lambda _message: None,
        )
        monkeypatch.setattr(
            chat_router_module,
            "extract_calculator_expression",
            lambda _message: None,
        )
        monkeypatch.setattr(
            chat_router_module,
            "extract_code_request",
            lambda _message: None,
        )
        monkeypatch.setattr(
            chat_router_module,
            "extract_data_analysis_request",
            lambda _message: None,
        )
        monkeypatch.setattr(
            chat_router_module,
            "extract_web_search_query",
            lambda _message: None,
        )
        monkeypatch.setattr(
            chat_router_module,
            "_build_history",
            lambda *_args, **_kwargs: [],
        )

        async def fake_augment(*_args, **_kwargs):
            return "isolated acceptance prompt", []

        monkeypatch.setattr(chat_router_module, "_augment_message", fake_augment)

        async def run_acceptance():
            provider_waiting = asyncio.Event()
            allow_provider_to_finish = asyncio.Event()

            async def blocked_provider(*_args, **kwargs):
                provider_waiting.set()
                await allow_provider_to_finish.wait()
                on_provider_selected = kwargs.get("on_provider_selected")
                if callable(on_provider_selected):
                    on_provider_selected("isolated-test-provider")
                yield "pool-slot-available"

            monkeypatch.setattr(
                chat_router_module, "stream_ai_reply", blocked_provider
            )

            async def client_is_connected():
                return False

            request = SimpleNamespace(
                headers={"accept-language": "en"},
                is_disconnected=client_is_connected,
            )
            response = await chat_router_module.chat_stream(
                payload=SimpleNamespace(
                    message="Test bounded PostgreSQL pool behavior",
                    file_ids=[],
                    conversation_id=conversation_id,
                ),
                request=request,
                current_user=SimpleNamespace(
                    id=user_id,
                    email=f"sse-pool-acceptance-{suffix}@example.invalid",
                ),
                db=db,
            )
            assert response.media_type == "text/event-stream"
            assert db.expire_on_commit is False

            iterator = response.body_iterator
            try:
                first_event = await iterator.__anext__()
                second_event = await iterator.__anext__()
                assert "event: conversation" in first_event
                assert "event: sources" in second_event

                pending_chunk = asyncio.create_task(iterator.__anext__())
                try:
                    # Do not proceed until the mocked AI provider is actually blocked.
                    await asyncio.wait_for(provider_waiting.wait(), timeout=5)

                    # This is the core acceptance assertion: SSE still owns a Session,
                    # but must not retain the only physical PostgreSQL connection.
                    assert pool_engine.pool.checkedout() == 0

                    second_request_session = PoolSession()
                    try:
                        assert (
                            second_request_session.execute(text("SELECT 42")).scalar_one()
                            == 42
                        )
                        assert pool_engine.pool.checkedout() == 1
                    finally:
                        second_request_session.close()

                    assert pool_engine.pool.checkedout() == 0
                finally:
                    allow_provider_to_finish.set()

                chunk_event = await asyncio.wait_for(pending_chunk, timeout=5)
                assert "event: chunk" in chunk_event
                assert "pool-slot-available" in chunk_event

                remaining_events = []
                while True:
                    try:
                        remaining_events.append(
                            await asyncio.wait_for(iterator.__anext__(), timeout=5)
                        )
                    except StopAsyncIteration:
                        break

                assert any("event: done" in event for event in remaining_events)
                assert pool_engine.pool.checkedout() == 0
            finally:
                # Ensure the async generator is closed on the same event loop,
                # including when an assertion fails before the stream completes.
                allow_provider_to_finish.set()
                close_iterator = getattr(iterator, "aclose", None)
                if close_iterator is not None:
                    await close_iterator()

        asyncio.run(run_acceptance())
    finally:
        try:
            db.rollback()
            if conversation_id is not None:
                db.query(Message).filter(
                    Message.conversation_id == conversation_id
                ).delete(synchronize_session=False)
                db.query(Conversation).filter(
                    Conversation.id == conversation_id
                ).delete(synchronize_session=False)
            if workspace_id is not None:
                db.query(Workspace).filter(
                    Workspace.id == workspace_id
                ).delete(synchronize_session=False)
            if user_id is not None:
                db.query(UsageLog).filter(
                    UsageLog.user_id == user_id
                ).delete(synchronize_session=False)
                db.query(User).filter(User.id == user_id).delete(
                    synchronize_session=False
                )
            db.commit()
        finally:
            db.close()
            pool_engine.dispose()
