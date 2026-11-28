"""
تسجيل أحداث مهمة بجدول audit_logs (تظهر بلوحة الإدارة) + بالـ logger العادي بنفس الوقت
"""
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models.audit_log import AuditLog

logger = get_logger("audit")


def log_event(
    db: Session,
    event_type: str,
    description: str,
    user_id: int | None = None,
    workspace_id: int | None = None,
    *,
    commit: bool = True,
    emit_log: bool = True,
) -> None:
    """Record an audit event; callers may defer commit to their transaction boundary."""
    db.add(
        AuditLog(
            user_id=user_id,
            workspace_id=workspace_id,
            event_type=event_type,
            description=description,
        )
    )
    if commit:
        db.commit()
    if commit and emit_log:
        log_event_to_logger(event_type, description, workspace_id)


def log_event_to_logger(
    event_type: str,
    description: str,
    workspace_id: int | None = None,
) -> None:
    """Emit a sanitized application log after the transaction has committed."""
    scope = f" workspace={workspace_id}" if workspace_id is not None else ""
    # Descriptions may contain user-controlled text; keep them out of app logs.
    logger.info("[%s]%s", event_type, scope)
