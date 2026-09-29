"""
مهام خلفية (Celery) — البريد الإلكتروني + تنفيذ مهام AI المجدولة.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.logging_config import get_logger
from app.models.agent_job import AgentJob
from app.models.conversation import Conversation, Message, MessageRole
from app.models.scheduled_task import (
    ScheduledTask,
    ScheduledTaskExecutionMode,
    ScheduledTaskType,
)
from app.models.scheduled_task_run import ScheduledTaskRun, ScheduledTaskRunStatus
from app.models.usage_log import UsageLog
from app.models.user import User, UserRole
from app.models.workspace import Workspace, WorkspaceMember
from app.notifications import notify
from app.services.agent_runtime import AgentRuntime, get_agent_configuration_version, get_agent_tool_policy_snapshot
from app.services.ai_providers.factory import get_provider
from app.services.ai_service import get_ai_reply
from app.services.email_service import send_email
from app.dependencies import enforce_ai_cost_budget, get_daily_ai_limit

logger = get_logger("tasks")


class AgentJobCancelled(Exception):
    """Raised when a persistent Agent job is cancelled cooperatively."""


async def _agent_job_event_sink(db, job_id: int, event: dict) -> None:
    if event.get("type") not in {
        "runtime_round_start",
        "runtime_start",
        "start",
        "result",
    }:
        return

    job = db.get(AgentJob, job_id)
    if job is None or job.cancel_requested or job.status == "cancelled":
        raise AgentJobCancelled("تم إلغاء مهمة الوكيل.")


def _sync_scheduled_agent_run(
    db,
    job: AgentJob,
    *,
    succeeded: bool,
    conversation_id: int | None = None,
    error: str | None = None,
) -> None:
    run = (
        db.query(ScheduledTaskRun)
        .filter(ScheduledTaskRun.agent_job_id == job.id)
        .first()
    )
    if run is None:
        return
    run.status = (
        ScheduledTaskRunStatus.succeeded
        if succeeded
        else ScheduledTaskRunStatus.failed
    )
    run.finished_at = datetime.now(timezone.utc)
    if conversation_id is not None:
        run.conversation_id = conversation_id
    run.error = error


def _execute_agent_job(job_id: int, db=None) -> None:
    owns_session = db is None
    if db is None:
        db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        job = db.get(AgentJob, job_id)
        if job is None:
            return
        if job.status in {"succeeded", "failed", "cancelled"}:
            return
        if job.cancel_requested:
            job.status = "cancelled"
            job.finished_at = now
            _sync_scheduled_agent_run(
                db,
                job,
                succeeded=False,
                error="تم إلغاء المهمة المجدولة.",
            )
            db.commit()
            return

        user = db.get(User, job.user_id)
        workspace = db.get(Workspace, job.workspace_id)
        conversation = db.get(Conversation, job.conversation_id)
        if not user or not user.is_active or not workspace or not conversation:
            job.status = "failed"
            job.error = "المستخدم أو مساحة العمل أو المحادثة غير متاحة."
            job.finished_at = now
            _sync_scheduled_agent_run(
                db,
                job,
                succeeded=False,
                error=job.error,
            )
            db.commit()
            return

        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == user.id,
            )
            .first()
        )
        if not membership:
            job.status = "failed"
            job.error = "لم تعد تملك عضوية في مساحة العمل."
            job.finished_at = now
            _sync_scheduled_agent_run(
                db,
                job,
                succeeded=False,
                error=job.error,
            )
            db.commit()
            return

        _ensure_ai_quota(user, workspace, db)
        enforce_ai_cost_budget(user, db)

        model = workspace.default_ai_model
        provider = get_provider(model)
        job.status = "running"
        job.started_at = now
        job.error = None
        db.commit()

        async def event_sink(event: dict) -> None:
            await _agent_job_event_sink(db, job.id, event)

        result = asyncio.run(
            AgentRuntime(
                provider=provider,
                event_sink=event_sink,
            ).run(
                task=job.task,
                history=[],
                conversation=conversation,
                current_user=user,
                db=db,
            )
        )

        refreshed_job = db.get(AgentJob, job.id)
        if refreshed_job is None:
            return
        if refreshed_job.cancel_requested:
            refreshed_job.status = "cancelled"
            refreshed_job.finished_at = datetime.now(timezone.utc)
            refreshed_job.run_id = result.run_id
            refreshed_job.result_text = result.text
            refreshed_job.result_sources = result.sources
            refreshed_job.input_tokens = result.input_tokens
            refreshed_job.output_tokens = result.output_tokens
            _sync_scheduled_agent_run(
                db,
                refreshed_job,
                succeeded=False,
                conversation_id=conversation.id,
                error="تم إلغاء المهمة المجدولة.",
            )
            db.commit()
            return

        refreshed_job.run_id = result.run_id
        refreshed_job.result_text = result.text
        refreshed_job.result_sources = result.sources
        refreshed_job.input_tokens = result.input_tokens
        refreshed_job.output_tokens = result.output_tokens
        refreshed_job.finished_at = datetime.now(timezone.utc)

        if result.status == "completed":
            refreshed_job.status = "succeeded"
            db.add(
                Message(
                    conversation_id=conversation.id,
                    role=MessageRole.assistant,
                    content=result.text,
                    sources=result.sources or None,
                )
            )
            _sync_scheduled_agent_run(
                db,
                refreshed_job,
                succeeded=True,
                conversation_id=conversation.id,
            )
        else:
            refreshed_job.status = "failed"
            refreshed_job.error = (
                "توقف تشغيل الوكيل عند حد الأمان قبل إكمال المهمة."
            )
            _sync_scheduled_agent_run(
                db,
                refreshed_job,
                succeeded=False,
                conversation_id=conversation.id,
                error=refreshed_job.error,
            )

        db.add(
            UsageLog(
                user_id=user.id,
                workspace_id=workspace.id,
                endpoint=f"/agent-jobs/{job.id}",
                model=model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                provider=getattr(provider, "name", None) or settings.AI_PROVIDER,
            )
        )
        db.commit()

    except AgentJobCancelled:
        job = db.get(AgentJob, job_id)
        if job is not None:
            job.status = "cancelled"
            job.finished_at = datetime.now(timezone.utc)
            _sync_scheduled_agent_run(
                db,
                job,
                succeeded=False,
                error="تم إلغاء المهمة المجدولة.",
            )
            db.commit()
    except Exception as exc:
        logger.exception("Long-running agent job failed: %s", job_id)
        db.rollback()
        job = db.get(AgentJob, job_id)
        if job is not None:
            job.status = "failed"
            job.error = str(exc)[:1000]
            job.finished_at = datetime.now(timezone.utc)
            _sync_scheduled_agent_run(
                db,
                job,
                succeeded=False,
                error=job.error,
            )
            db.commit()
    finally:
        if owns_session:
            db.close()


def _index_image_file_job(file_id: int, model: str, db=None) -> None:
    """Index an image through Vision and pgvector.

    When called as a Celery task it owns a dedicated DB session. When called
    synchronously as an HTTP fallback it reuses the request session so newly
    uploaded rows inside a test/request transaction remain visible.
    """
    from app.models.file_attachment import FileAttachment
    from app.services.image_rag import index_image_file

    owns_session = db is None
    if db is None:
        db = SessionLocal()
    try:
        file = db.get(FileAttachment, file_id)
        if file is None:
            return
        if not file.content_type.startswith("image/"):
            file.processing_status = "failed"
            file.processing_error = "الملف ليس صورة."
            db.commit()
            return
        if file.processing_status == "ready" and file.extracted_text:
            return

        file.processing_status = "processing"
        file.processing_error = None
        db.commit()

        reply, indexed_chunks = asyncio.run(index_image_file(file, db, model))
        file.processing_status = "ready"
        file.processing_error = None
        db.add(
            UsageLog(
                user_id=file.user_id,
                workspace_id=file.workspace_id,
                endpoint="/files/index-image",
                model=model,
                provider=reply.provider,
                input_tokens=reply.input_tokens,
                output_tokens=reply.output_tokens,
                latency_ms=reply.latency_ms,
            )
        )
        db.commit()
        logger.info(
            "Image indexed file_id=%s chunks=%s",
            file.id,
            indexed_chunks,
        )
    except Exception as exc:
        logger.exception("Image indexing failed file_id=%s", file_id)
        if owns_session:
            db.rollback()
        file = db.get(FileAttachment, file_id)
        if file is not None:
            file.processing_status = "failed"
            file.processing_error = str(exc)[:1000]
            if owns_session:
                db.commit()
            else:
                db.flush()
    finally:
        if owns_session:
            db.close()


def _process_file_attachment(file_id: int, db=None) -> None:
    """Extract text and build RAG embeddings outside the upload request."""
    from pathlib import Path

    from app.models.file_attachment import FileAttachment
    from app.services.embeddings import EmbeddingServiceError
    from app.services.file_text_extractor import FileTextExtractionError, extract_text
    from app.services.rag import index_file_chunks
    from app.services.storage import materialize_file

    owns_session = db is None
    if db is None:
        db = SessionLocal()
    try:
        file = db.get(FileAttachment, file_id)
        if file is None or file.processing_status == "ready":
            return

        file.processing_status = "processing"
        file.processing_error = None
        db.commit()

        fallback_path = Path(settings.UPLOAD_DIR) / str(file.user_id) / file.stored_filename
        with materialize_file(file.object_key, fallback_path) as path:
            try:
                extracted = extract_text(path, file.content_type)
            except FileTextExtractionError as exc:
                file.processing_status = "failed"
                file.processing_error = str(exc)[:1000]
                db.commit()
                return

        file.extracted_text = extracted
        file.processing_status = "ready"
        db.flush()

        if extracted:
            try:
                index_file_chunks(db, file)
            except EmbeddingServiceError as exc:
                logger.warning("File RAG indexing failed file_id=%s: %s", file.id, exc)

        db.commit()
    except Exception as exc:
        logger.exception("File processing failed: %s", file_id)
        if owns_session:
            db.rollback()
        file = db.get(FileAttachment, file_id)
        if file is not None:
            file.processing_status = "failed"
            file.processing_error = str(exc)[:1000]
            if owns_session:
                db.commit()
            else:
                db.flush()
    finally:
        if owns_session:
            db.close()


def _next_occurrence(task: ScheduledTask, now: datetime) -> datetime | None:
    if task.schedule_type == ScheduledTaskType.once:
        return None

    tz = ZoneInfo(task.timezone_name or "UTC")
    local_next_run = task.next_run_at.astimezone(tz)
    local_now = now.astimezone(tz)
    delta = timedelta(
        days=1 if task.schedule_type == ScheduledTaskType.daily else 7
    )

    while local_next_run <= local_now:
        local_next_run += delta

    # نحافظ على وقت المستخدم المحلي في المنطقة الزمنية المحددة، ثم نخزن UTC.
    return local_next_run.astimezone(timezone.utc)


def _ensure_ai_quota(user: User, workspace: Workspace, db) -> None:
    if user.role == UserRole.admin:
        return

    since = datetime.now(timezone.utc) - timedelta(days=1)
    personal_limit = get_daily_ai_limit(user, db)
    personal_used = (
        db.query(UsageLog)
        .filter(
            UsageLog.user_id == user.id,
            UsageLog.created_at >= since,
        )
        .count()
    )
    if personal_used >= personal_limit:
        raise RuntimeError(
            f"تم الوصول إلى الحد اليومي للمستخدم ({personal_limit} طلب)."
        )

    if workspace.daily_ai_request_limit is not None:
        workspace_used = (
            db.query(UsageLog)
            .filter(
                UsageLog.workspace_id == workspace.id,
                UsageLog.created_at >= since,
            )
            .count()
        )
        if workspace_used >= workspace.daily_ai_request_limit:
            raise RuntimeError(
                f"تم الوصول إلى حد مساحة العمل اليومي ({workspace.daily_ai_request_limit} طلب)."
            )


def _execute_scheduled_task(
    task_id: int,
    run_id: int | None = None,
    db=None,
) -> None:
    owns_session = db is None
    if db is None:
        db = SessionLocal()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    try:
        task = db.get(ScheduledTask, task_id)
        if not task or (run_id is None and not task.is_active):
            return

        run = db.get(ScheduledTaskRun, run_id) if run_id is not None else None
        if run is None:
            run = ScheduledTaskRun(
                scheduled_task_id=task.id,
                user_id=task.user_id,
                workspace_id=task.workspace_id,
                prompt=task.prompt,
                status=ScheduledTaskRunStatus.queued,
            )
            db.add(run)
            db.flush()
        else:
            run.prompt = task.prompt

        run.status = ScheduledTaskRunStatus.running
        run.started_at = now
        run.error = None
        db.commit()

        user = db.get(User, task.user_id)
        workspace = db.get(Workspace, task.workspace_id)
        if not user or not user.is_active or not workspace:
            task.is_active = False
            task.last_error = "المستخدم أو مساحة العمل غير متاحة."
            task.last_run_at = now
            run.status = ScheduledTaskRunStatus.failed
            run.finished_at = now
            run.error = task.last_error
            db.commit()
            return

        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == user.id,
            )
            .first()
        )
        if not membership:
            task.is_active = False
            task.last_error = "لم تعد تملك عضوية في مساحة العمل."
            task.last_run_at = now
            run.status = ScheduledTaskRunStatus.failed
            run.finished_at = now
            run.error = task.last_error
            db.commit()
            return

        _ensure_ai_quota(user, workspace, db)
        enforce_ai_cost_budget(user, db)

        ai_model = workspace.default_ai_model

        if task.execution_mode == ScheduledTaskExecutionMode.agent:
            title = f"Scheduled Agent: {task.prompt[:70]}".strip()
            conversation = Conversation(
                user_id=user.id,
                workspace_id=workspace.id,
                title=title,
                ai_model=ai_model,
            )
            db.add(conversation)
            db.flush()
            db.add(
                Message(
                    conversation_id=conversation.id,
                    role=MessageRole.user,
                    content=task.prompt,
                )
            )
            job = AgentJob(
                user_id=user.id,
                workspace_id=workspace.id,
                conversation_id=conversation.id,
                task=task.prompt,
                status="queued",
                agent_version=get_agent_configuration_version(),
                tool_policy_snapshot=get_agent_tool_policy_snapshot(),
            )
            db.add(job)
            db.flush()

            run.agent_job_id = job.id
            run.status = ScheduledTaskRunStatus.queued
            run.conversation_id = conversation.id
            task.last_run_at = now
            task.last_error = None
            next_run = _next_occurrence(task, now)
            if next_run is None:
                task.next_run_at = now
                task.is_active = False
            else:
                task.next_run_at = next_run
            db.commit()

            try:
                if execute_agent_job is not None:
                    execute_agent_job.delay(job.id)
                else:
                    _execute_agent_job(job.id, db=db)
            except Exception as exc:
                logger.exception(
                    "Failed to enqueue scheduled Agent job task_id=%s job_id=%s",
                    task.id,
                    job.id,
                )
                refreshed_job = db.get(AgentJob, job.id)
                if refreshed_job is not None:
                    refreshed_job.status = "failed"
                    refreshed_job.error = "تعذر جدولة Agent job."
                    refreshed_job.finished_at = datetime.now(timezone.utc)
                    _sync_scheduled_agent_run(
                        db,
                        refreshed_job,
                        succeeded=False,
                        conversation_id=conversation.id,
                        error=refreshed_job.error,
                    )
                    task.last_error = str(exc)[:500]
                    db.commit()
            return

        reply = asyncio.run(get_ai_reply(task.prompt, [], ai_model))

        title_prefix = "Scheduled" if not task.prompt.startswith("م") else "مهمة مجدولة"
        title = f"{title_prefix}: {task.prompt[:70]}".strip()

        conversation = Conversation(
            user_id=user.id,
            workspace_id=workspace.id,
            title=title,
            ai_model=ai_model,
        )
        db.add(conversation)
        db.flush()

        db.add(
            Message(
                conversation_id=conversation.id,
                role=MessageRole.user,
                content=task.prompt,
            )
        )
        db.add(
            Message(
                conversation_id=conversation.id,
                role=MessageRole.assistant,
                content=reply.text,
            )
        )
        db.add(
            UsageLog(
                user_id=user.id,
                workspace_id=workspace.id,
                endpoint=f"/scheduled-tasks/{task.id}",
                model=ai_model,
                input_tokens=reply.input_tokens,
                output_tokens=reply.output_tokens,
                provider=reply.provider,
                latency_ms=reply.latency_ms,
            )
        )

        run.status = ScheduledTaskRunStatus.succeeded
        run.finished_at = now
        run.conversation_id = conversation.id
        run.error = None

        task.last_run_at = now
        task.last_error = None
        next_run = _next_occurrence(task, now)
        if next_run is None:
            task.next_run_at = now
            task.is_active = False
        else:
            task.next_run_at = next_run

        db.commit()

        try:
            notification = notify(
                db,
                user.id,
                "تم تنفيذ المهمة المجدولة",
                f"تم تشغيل: {title}",
                "scheduled_task",
            )
            logger.info(
                "Scheduled task completed: task_id=%s conversation_id=%s notification_id=%s",
                task.id,
                conversation.id,
                notification.id,
            )
        except Exception:
            logger.exception("Failed to create notification for scheduled task %s", task.id)

    except Exception as exc:
        logger.exception("Scheduled task failed: %s", task_id)
        # عند استخدام fallback داخل طلب HTTP، تكون Session مملوكة للمسار
        # وقد تكون فيها معاملة اختبار خارجية. لا نسوي rollback للـ Session
        # المستلمة حتى لا نفقد سجل التنفيذ الذي أنشأناه قبل تشغيل المزود.
        if owns_session:
            db.rollback()

        task = db.get(ScheduledTask, task_id)
        run = db.get(ScheduledTaskRun, run_id) if run_id is not None else None
        if run is not None:
            run.status = ScheduledTaskRunStatus.failed
            run.finished_at = now
            run.error = str(exc)[:500]
        if task:
            task.last_run_at = now
            task.last_error = str(exc)[:500]
            next_run = _next_occurrence(task, now)
            if next_run is None:
                task.next_run_at = now
                task.is_active = False
            else:
                task.next_run_at = next_run
            db.commit()

            try:
                notify(
                    db,
                    task.user_id,
                    "فشل تنفيذ المهمة المجدولة",
                    f"تعذر تنفيذ المهمة: {task.prompt[:120]}",
                    "scheduled_task_error",
                )
            except Exception:
                logger.exception("Failed to notify about scheduled task error %s", task_id)
    finally:
        if owns_session:
            db.close()


def _run_due_scheduled_tasks() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due_tasks = (
            db.query(ScheduledTask.id, ScheduledTask.next_run_at)
            .filter(
                ScheduledTask.is_active.is_(True),
                ScheduledTask.next_run_at <= now,
            )
            .order_by(ScheduledTask.next_run_at.asc(), ScheduledTask.id.asc())
            .limit(50)
            .all()
        )
        due_slots = [(row[0], row[1]) for row in due_tasks]
    finally:
        db.close()

    for task_id, scheduled_for in due_slots:
        claim_db = SessionLocal()
        try:
            task = claim_db.get(ScheduledTask, task_id)
            if not task or not task.is_active or task.next_run_at != scheduled_for:
                continue

            run = ScheduledTaskRun(
                scheduled_task_id=task.id,
                user_id=task.user_id,
                workspace_id=task.workspace_id,
                prompt=task.prompt,
                scheduled_for=scheduled_for,
                status=ScheduledTaskRunStatus.queued,
            )
            claim_db.add(run)
            try:
                claim_db.commit()
                run_id = run.id
            except IntegrityError:
                # عامل آخر سبق أن حجز نفس الموعد — لا ننفذ المهمة مرتين.
                claim_db.rollback()
                continue
        finally:
            claim_db.close()

        _execute_scheduled_task(task_id, run_id)


try:
    from celery import Celery

    from app.config import settings

    celery_app = Celery(
        "ai_backend",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )
    celery_app.conf.timezone = "UTC"
    celery_app.conf.beat_schedule = {
        "run-due-scheduled-tasks": {
            "task": "run_due_scheduled_tasks",
            "schedule": 60.0,
        }
    }

    @celery_app.task(name="index_image_file")
    def index_image_file_task(file_id: int, model: str) -> None:
        _index_image_file_job(file_id, model)

    @celery_app.task(name="process_file_attachment")
    def process_file_attachment(file_id: int) -> None:
        _process_file_attachment(file_id)

    @celery_app.task(name="send_email_task")
    def send_email_task(to: str, subject: str, body: str) -> None:
        send_email(to, subject, body)

    @celery_app.task(name="execute_scheduled_task")
    def execute_scheduled_task(task_id: int, run_id: int) -> None:
        _execute_scheduled_task(task_id, run_id)

    @celery_app.task(name="execute_agent_job")
    def execute_agent_job(job_id: int) -> None:
        _execute_agent_job(job_id)

    @celery_app.task(name="deliver_webhook_task")
    def deliver_webhook_task(delivery_id: int) -> None:
        from app.services.webhook_service import deliver_webhook_delivery

        deliver_webhook_delivery(delivery_id)


    @celery_app.task(name="run_due_scheduled_tasks")
    def run_due_scheduled_tasks() -> None:
        _run_due_scheduled_tasks()

    _CELERY_AVAILABLE = True
except ImportError:
    celery_app = None
    send_email_task = None
    execute_scheduled_task = None
    execute_agent_job = None
    index_image_file_task = None
    process_file_attachment = None
    run_due_scheduled_tasks = None
    _CELERY_AVAILABLE = False
    logger.info("مكتبة celery غير مثبّتة — المهام الخلفية غير مفعّلة")


def queue_email(to: str, subject: str, body: str) -> None:
    """يحاول جدولة الإيميل عبر Celery؛ لو مو متاح أو فشل الاتصال بـ Redis، يرسله مباشرة."""
    if _CELERY_AVAILABLE:
        try:
            send_email_task.delay(to, subject, body)
            return
        except Exception:
            logger.warning("تعذر إرسال المهمة لـ Celery/Redis — إرسال مباشر بدلها")
    send_email(to, subject, body)
