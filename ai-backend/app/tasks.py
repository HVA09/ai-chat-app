"""
مهام خلفية (Celery) — البريد الإلكتروني + تنفيذ مهام AI المجدولة.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.logging_config import get_logger
from app.models.conversation import Conversation, Message, MessageRole
from app.models.notification import Notification
from app.models.scheduled_task import ScheduledTask, ScheduledTaskType
from app.models.usage_log import UsageLog
from app.models.user import User, UserRole
from app.models.workspace import Workspace, WorkspaceMember
from app.notifications import notify
from app.services.ai_providers.factory import get_provider
from app.services.ai_service import get_ai_reply
from app.services.email_service import send_email
from app.dependencies import get_daily_ai_limit

logger = get_logger("tasks")


def _next_occurrence(task: ScheduledTask, now: datetime) -> datetime | None:
    if task.schedule_type == ScheduledTaskType.once:
        return None

    delta = timedelta(
        days=1 if task.schedule_type == ScheduledTaskType.daily else 7
    )
    next_run = task.next_run_at
    while next_run <= now:
        next_run += delta
    return next_run


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


def _execute_scheduled_task(task_id: int) -> None:
    db = SessionLocal()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    try:
        task = db.get(ScheduledTask, task_id)
        if not task or not task.is_active:
            return

        user = db.get(User, task.user_id)
        workspace = db.get(Workspace, task.workspace_id)
        if not user or not user.is_active or not workspace:
            task.is_active = False
            task.last_error = "المستخدم أو مساحة العمل غير متاحة."
            task.last_run_at = now
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
            db.commit()
            return

        _ensure_ai_quota(user, workspace, db)

        ai_model = workspace.default_ai_model
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
                input_tokens=reply.input_tokens,
                output_tokens=reply.output_tokens,
            )
        )

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
        db.rollback()
        task = db.get(ScheduledTask, task_id)
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
        db.close()


def _run_due_scheduled_tasks() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due_tasks = (
            db.query(ScheduledTask.id)
            .filter(
                ScheduledTask.is_active.is_(True),
                ScheduledTask.next_run_at <= now,
            )
            .order_by(ScheduledTask.next_run_at.asc(), ScheduledTask.id.asc())
            .limit(50)
            .all()
        )
        task_ids = [row[0] for row in due_tasks]
    finally:
        db.close()

    for task_id in task_ids:
        _execute_scheduled_task(task_id)


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

    @celery_app.task(name="send_email_task")
    def send_email_task(to: str, subject: str, body: str) -> None:
        send_email(to, subject, body)

    @celery_app.task(name="run_due_scheduled_tasks")
    def run_due_scheduled_tasks() -> None:
        _run_due_scheduled_tasks()

    _CELERY_AVAILABLE = True
except ImportError:
    celery_app = None
    send_email_task = None
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
