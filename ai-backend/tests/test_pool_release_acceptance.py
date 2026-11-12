"""Acceptance tests for bounded PostgreSQL pools during blocked external I/O."""

import asyncio
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.models.agent_job import AgentJob
from app.models.conversation import Conversation, Message
from app.models.conversation_file_link import ConversationFileLink
from app.models.file_attachment import FileAttachment
from app.models.file_chunk import FileChunk
from app.models.usage_log import UsageLog
from app.models.user import User
from app.models.workspace import Workspace
from app.routers import chat as chat_router_module
from app import tasks as tasks_module
from app.services.ai_providers.base import AIReply
from app.services import image_rag, rag


def _local_ci_database_url() -> str:
    """Refuse every database target except the disposable local CI test database."""
    value = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/ai_backend_test",
    )
    parsed = make_url(value)
    if (
        parsed.drivername.split("+", 1)[0] != "postgresql"
        or parsed.host not in {"localhost", "127.0.0.1"}
        or parsed.port != 5432
        or parsed.database != "ai_backend_test"
        or parsed.query
    ):
        pytest.skip(
            "Pool acceptance tests require the isolated localhost:5432/ai_backend_test "
            "database with no URL query or routing overrides"
        )
    return value


def _create_scenario(session_factory):
    """Create uniquely named rows in the pre-existing test schema; do not mutate schema."""
    suffix = uuid.uuid4().hex
    db = session_factory()
    try:
        user = User(
            email=f"pool-acceptance-{suffix}@example.test",
            hashed_password="test-only-not-a-real-password-hash",
        )
        db.add(user)
        db.flush()

        workspace = Workspace(owner_id=user.id, name=f"Pool acceptance {suffix}")
        db.add(workspace)
        db.flush()

        conversation = Conversation(
            user_id=user.id,
            workspace_id=workspace.id,
            title="Pool release acceptance",
            ai_model="pool-acceptance-model",
        )
        db.add(conversation)
        db.flush()

        attachment = FileAttachment(
            user_id=user.id,
            workspace_id=workspace.id,
            original_filename="pool-evidence.png",
            stored_filename=f"{suffix}.png",
            object_key=f"test-only/{suffix}.png",
            content_type="image/png",
            size_bytes=8,
            extracted_text="isolated pool acceptance evidence",
        )
        db.add(attachment)
        db.flush()
        db.add_all(
            [
                ConversationFileLink(
                    conversation_id=conversation.id,
                    file_id=attachment.id,
                ),
                FileChunk(
                    file_id=attachment.id,
                    chunk_index=0,
                    content="A test-only chunk used to exercise RAG retrieval.",
                    embedding=[0.1] * 768,
                ),
            ]
        )
        db.commit()
        return {
            "user_id": user.id,
            "workspace_id": workspace.id,
            "conversation_id": conversation.id,
            "file_id": attachment.id,
            "email": user.email,
        }
    finally:
        db.close()


def _delete_scenario(session_factory, scenario):
    """Delete only the uniquely identified rows created by this test."""
    db = session_factory()
    try:
        db.query(ConversationFileLink).filter(
            ConversationFileLink.conversation_id == scenario["conversation_id"]
        ).delete(synchronize_session=False)
        db.query(FileChunk).filter(
            FileChunk.file_id == scenario["file_id"]
        ).delete(synchronize_session=False)
        db.query(Message).filter(
            Message.conversation_id == scenario["conversation_id"]
        ).delete(synchronize_session=False)
        db.query(UsageLog).filter(
            UsageLog.user_id == scenario["user_id"]
        ).delete(synchronize_session=False)
        db.query(FileAttachment).filter(
            FileAttachment.id == scenario["file_id"]
        ).delete(synchronize_session=False)
        db.query(Conversation).filter(
            Conversation.id == scenario["conversation_id"]
        ).delete(synchronize_session=False)
        db.query(Workspace).filter(
            Workspace.id == scenario["workspace_id"]
        ).delete(synchronize_session=False)
        db.query(User).filter(
            User.id == scenario["user_id"]
        ).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


@pytest.mark.parametrize(
    "operation",
    ["chat_provider", "web_search", "vision_provider", "rag_embedding"],
)
def test_second_session_can_use_only_pool_slot_while_external_io_is_blocked(
    operation, monkeypatch, tmp_path
):
    """Exercise real route/service boundaries with a blocked mock and a one-slot PG pool."""
    database_url = _local_ci_database_url()
    pool_engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=1,
        max_overflow=0,
        pool_timeout=1,
        pool_pre_ping=True,
    )
    PoolSession = sessionmaker(
        bind=pool_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=True,
    )
    scenario = None
    try:
        scenario = _create_scenario(PoolSession)

        def run_acceptance():
            db = PoolSession()
            external_io_started = asyncio.Event()
            resume_external_io = asyncio.Event()
            request_task = None
            try:
                current_user = db.get(User, scenario["user_id"])
                conversation = db.get(Conversation, scenario["conversation_id"])
                assert current_user is not None
                assert conversation is not None
                assert db.expire_on_commit is True

                async def wait_for_external_release():
                    external_io_started.set()
                    await asyncio.wait_for(resume_external_io.wait(), timeout=5)

                if operation in {"chat_provider", "web_search"}:
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
                        chat_router_module, "extract_agent_request", lambda _message: None
                    )
                    monkeypatch.setattr(
                        chat_router_module,
                        "extract_calculator_expression",
                        lambda _message: None,
                    )
                    monkeypatch.setattr(
                        chat_router_module, "extract_code_request", lambda _message: None
                    )
                    monkeypatch.setattr(
                        chat_router_module,
                        "extract_data_analysis_request",
                        lambda _message: None,
                    )
                    monkeypatch.setattr(
                        chat_router_module,
                        "extract_web_search_query",
                        (lambda _message: "connection pool acceptance")
                        if operation == "web_search"
                        else (lambda _message: None),
                    )

                    if operation == "chat_provider":
                        async def blocked_provider(*_args, **_kwargs):
                            await wait_for_external_release()
                            return AIReply(
                                text="provider completed",
                                input_tokens=1,
                                output_tokens=1,
                            )

                        monkeypatch.setattr(
                            chat_router_module, "_build_history", lambda *_args: []
                        )
                        monkeypatch.setattr(
                            chat_router_module,
                            "_augment_message",
                            _async_value(("pool acceptance prompt", [])),
                        )
                        monkeypatch.setattr(
                            chat_router_module, "get_ai_reply", blocked_provider
                        )
                        invoke = lambda: chat_router_module.chat(
                            SimpleNamespace(
                                message="Explain bounded database connection pools.",
                                file_ids=[],
                                conversation_id=conversation.id,
                            ),
                            current_user,
                            db,
                        )
                        expected_reply = "provider completed"
                    else:
                        async def blocked_search(*_args, **_kwargs):
                            await wait_for_external_release()
                            return [{"title": "isolated test result"}]

                        monkeypatch.setattr(
                            chat_router_module, "search_web", blocked_search
                        )
                        monkeypatch.setattr(
                            chat_router_module,
                            "format_web_search_response",
                            lambda *_args: ("search completed", []),
                        )
                        invoke = lambda: chat_router_module.chat(
                            SimpleNamespace(
                                message="Search for connection pool acceptance.",
                                file_ids=[],
                                conversation_id=conversation.id,
                            ),
                            current_user,
                            db,
                        )
                        expected_reply = "search completed"

                elif operation == "vision_provider":
                    monkeypatch.setattr(
                        chat_router_module,
                        "enforce_workspace_daily_ai_limit",
                        lambda *_args, **_kwargs: None,
                    )
                    image_path = tmp_path / f"{scenario['file_id']}.png"
                    image_path.write_bytes(b"\x89PNG\r\n")
                    monkeypatch.setattr(
                        chat_router_module,
                        "materialize_file",
                        lambda *_args, **_kwargs: nullcontext(image_path),
                    )

                    async def blocked_vision(*_args, **_kwargs):
                        await wait_for_external_release()
                        return AIReply(
                            text="vision completed",
                            input_tokens=1,
                            output_tokens=1,
                            provider="test",
                            latency_ms=1,
                        )

                    monkeypatch.setattr(
                        chat_router_module, "get_ai_vision_reply", blocked_vision
                    )
                    invoke = lambda: chat_router_module.analyze_attached_image(
                        SimpleNamespace(
                            conversation_id=conversation.id,
                            file_id=scenario["file_id"],
                            message="Describe this test image.",
                        ),
                        current_user,
                        db,
                    )
                    expected_reply = "vision completed"

                else:
                    async def blocked_embedding(_query):
                        await wait_for_external_release()
                        return [0.1] * 768

                    monkeypatch.setattr(rag, "embed_query", blocked_embedding)

                    invoke = lambda: rag.retrieve_relevant_chunks(
                        db,
                        current_user.id,
                        conversation.id,
                        "test-only retrieval query",
                        workspace_id=conversation.workspace_id,
                    )
                    expected_reply = None

                async def exercise():
                    nonlocal request_task
                    request_task = asyncio.create_task(invoke())
                    try:
                        await asyncio.wait_for(external_io_started.wait(), timeout=5)

                        # The real route/service has crossed its commit-and-release boundary.
                        assert pool_engine.pool.checkedout() == 0
                        assert db.expire_on_commit is True

                        contender = PoolSession()
                        try:
                            assert contender.execute(text("SELECT 42")).scalar_one() == 42
                        finally:
                            contender.close()
                        assert pool_engine.pool.checkedout() == 0

                        resume_external_io.set()
                        result = await asyncio.wait_for(request_task, timeout=10)
                        if operation == "rag_embedding":
                            assert len(result) == 1
                            assert result[0][0].content.startswith("A test-only chunk")
                        else:
                            assert result.reply == expected_reply
                    finally:
                        # Unblock the request in the same event loop even when an
                        # assertion fails, so no task is stranded on a closed loop.
                        resume_external_io.set()
                        if request_task is not None and not request_task.done():
                            try:
                                await asyncio.wait_for(request_task, timeout=10)
                            except Exception:
                                pass

                asyncio.run(exercise())
            finally:
                db.close()

        run_acceptance()
    finally:
        if scenario is not None:
            _delete_scenario(PoolSession, scenario)
        pool_engine.dispose()


def _async_value(value):
    async def return_value(*_args, **_kwargs):
        return value

    return return_value

def test_second_session_can_use_pool_slot_during_blocked_image_embeddings(
    monkeypatch, tmp_path
):
    """The image description must be committed/released before synchronous embeddings."""
    database_url = _local_ci_database_url()
    pool_engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=1,
        max_overflow=0,
        pool_timeout=1,
        pool_pre_ping=True,
    )
    PoolSession = sessionmaker(
        bind=pool_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=True,
    )
    scenario = None
    embedding_started = threading.Event()
    resume_embedding = threading.Event()
    try:
        scenario = _create_scenario(PoolSession)
        image_path = tmp_path / f"{scenario['file_id']}.png"
        image_path.write_bytes(b"\x89PNG\r\n")

        monkeypatch.setattr(
            image_rag,
            "materialize_file",
            lambda *_args, **_kwargs: nullcontext(image_path),
        )

        async def fake_vision(*_args, **_kwargs):
            return AIReply(
                text="A test-only image description.",
                input_tokens=1,
                output_tokens=1,
                provider="test",
                latency_ms=1,
            )

        monkeypatch.setattr(image_rag, "get_ai_vision_reply", fake_vision)

        def blocked_index_file_chunks(db, file):
            assert file.extracted_text == (
                "[IMAGE DESCRIPTION] A test-only image description."
            )
            assert db.expire_on_commit is True
            embedding_started.set()
            if not resume_embedding.wait(timeout=5):
                raise TimeoutError("test did not resume the mocked embeddings operation")
            return 1

        monkeypatch.setattr(image_rag, "index_file_chunks", blocked_index_file_chunks)

        def run_image_indexing():
            db = PoolSession()
            try:
                attachment = db.get(FileAttachment, scenario["file_id"])
                assert attachment is not None
                assert db.expire_on_commit is True
                return asyncio.run(
                    image_rag.index_image_file(
                        attachment,
                        db,
                        "pool-acceptance-model",
                    )
                )
            finally:
                db.close()

        with ThreadPoolExecutor(
            max_workers=1
        ) as executor:
            future = executor.submit(run_image_indexing)
            try:
                assert embedding_started.wait(timeout=5)
                assert pool_engine.pool.checkedout() == 0

                contender = PoolSession()
                try:
                    assert contender.execute(text("SELECT 42")).scalar_one() == 42
                finally:
                    contender.close()
                assert pool_engine.pool.checkedout() == 0

                resume_embedding.set()
                reply, indexed_chunks = future.result(timeout=10)
                assert reply.text == "A test-only image description."
                assert indexed_chunks == 1
            finally:
                resume_embedding.set()
                if not future.done():
                    future.result(timeout=10)

        verify = PoolSession()
        try:
            attachment = verify.get(FileAttachment, scenario["file_id"])
            assert attachment is not None
            assert attachment.extracted_text == (
                "[IMAGE DESCRIPTION] A test-only image description."
            )
        finally:
            verify.close()
    finally:
        resume_embedding.set()
        if scenario is not None:
            _delete_scenario(PoolSession, scenario)
        pool_engine.dispose()


def test_agent_event_sink_releases_db_pool_before_provider_wait():
    """A read-only Agent event must not hold a pool slot during provider I/O."""
    database_url = _local_ci_database_url()
    pool_engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=1,
        max_overflow=0,
        pool_timeout=1,
        pool_pre_ping=True,
    )
    PoolSession = sessionmaker(
        bind=pool_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=True,
    )
    scenario = None
    job_id = None
    db = None
    allow_provider_to_finish = asyncio.Event()
    provider_waiting = asyncio.Event()
    try:
        scenario = _create_scenario(PoolSession)
        setup = PoolSession()
        try:
            job = AgentJob(
                user_id=scenario["user_id"],
                workspace_id=scenario["workspace_id"],
                conversation_id=scenario["conversation_id"],
                task="Test provider wait does not retain a database checkout.",
                status="running",
            )
            setup.add(job)
            setup.commit()
            job_id = job.id
        finally:
            setup.close()

        db = PoolSession()

        async def blocked_provider():
            await tasks_module._agent_job_event_sink(
                db,
                job_id,
                {"type": "runtime_start"},
            )
            assert pool_engine.pool.checkedout() == 0
            provider_waiting.set()
            await asyncio.wait_for(allow_provider_to_finish.wait(), timeout=5)

        async def exercise():
            provider_task = asyncio.create_task(blocked_provider())
            try:
                await asyncio.wait_for(provider_waiting.wait(), timeout=5)
                assert pool_engine.pool.checkedout() == 0

                contender = PoolSession()
                try:
                    assert contender.execute(text("SELECT 42")).scalar_one() == 42
                finally:
                    contender.close()

                assert pool_engine.pool.checkedout() == 0
            finally:
                allow_provider_to_finish.set()
                await asyncio.wait_for(provider_task, timeout=5)

        asyncio.run(exercise())
    finally:
        allow_provider_to_finish.set()
        if db is not None:
            db.close()
        if job_id is not None:
            cleanup = PoolSession()
            try:
                cleanup.query(AgentJob).filter(AgentJob.id == job_id).delete(
                    synchronize_session=False
                )
                cleanup.commit()
            finally:
                cleanup.close()
        if scenario is not None:
            _delete_scenario(PoolSession, scenario)
        pool_engine.dispose()
