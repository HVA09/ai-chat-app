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
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            workspace_id=workspace_id,
            event_type=event_type,
            description=description,
        )
    )
    db.commit()
    scope = f" workspace={workspace_id}" if workspace_id is not None else ""
    logger.info("[%s]%s %s", event_type, scope, description)
