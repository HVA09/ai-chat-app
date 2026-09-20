"""
مسارات لوحة الإدارة — Authorization بحسب الدور (role-based)، admin فقط
"""
import csv
import io
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.audit import log_event
from app.cache import cache_get, cache_set
from app.config import settings as app_settings
from app.database import get_db
from app.dependencies import require_admin
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation, Message
from app.models.file_attachment import FileAttachment
from app.models.usage_log import UsageLog
from app.models.user import User
from app.schemas.admin import (
    AdminConversationOut,
    AdminStats,
    AdminUserOut,
    AdminUserUpdate,
    AuditLogOut,
    DailyStatsPoint,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats", response_model=AdminStats)
def get_stats(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    cache_key = "admin:stats"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    stats = AdminStats(
        total_users=db.query(func.count(User.id)).scalar(),
        total_conversations=db.query(func.count(Conversation.id)).scalar(),
        total_messages=db.query(func.count(Message.id)).scalar(),
        total_ai_requests=db.query(func.count(UsageLog.id)).scalar(),
        total_files=db.query(func.count(FileAttachment.id)).scalar(),
        storage_used_bytes=db.query(func.coalesce(func.sum(FileAttachment.size_bytes), 0)).scalar(),
    )
    result = stats.model_dump()
    cache_set(cache_key, result, app_settings.CACHE_TTL_SECONDS)
    return result


def _compute_daily_stats(db: Session, days: int) -> list[DailyStatsPoint]:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    def _by_day(rows) -> dict:
        return {row[0].date(): row[1:] for row in rows}

    users_rows = (
        db.query(func.date_trunc("day", User.created_at), func.count(User.id))
        .filter(User.created_at >= since)
        .group_by(func.date_trunc("day", User.created_at))
        .all()
    )
    conversations_rows = (
        db.query(func.date_trunc("day", Conversation.created_at), func.count(Conversation.id))
        .filter(Conversation.created_at >= since)
        .group_by(func.date_trunc("day", Conversation.created_at))
        .all()
    )
    usage_rows = (
        db.query(
            func.date_trunc("day", UsageLog.created_at),
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.input_tokens), 0),
            func.coalesce(func.sum(UsageLog.output_tokens), 0),
        )
        .filter(UsageLog.created_at >= since)
        .group_by(func.date_trunc("day", UsageLog.created_at))
        .all()
    )

    users_map = _by_day(users_rows)
    conversations_map = _by_day(conversations_rows)
    usage_map = _by_day(usage_rows)

    points = []
    for offset in range(days, -1, -1):
        day = (datetime.now(timezone.utc) - timedelta(days=offset)).date()
        requests, in_tok, out_tok = usage_map.get(day, (0, 0, 0))
        points.append(
            DailyStatsPoint(
                date=day.isoformat(),
                new_users=(users_map.get(day, (0,)))[0],
                new_conversations=(conversations_map.get(day, (0,)))[0],
                ai_requests=requests,
                input_tokens=in_tok,
                output_tokens=out_tok,
            )
        )
    return points


@router.get("/analytics/daily", response_model=list[DailyStatsPoint])
def get_daily_analytics(
    days: int = 30,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return _compute_daily_stats(db, days)


@router.get("/analytics/export.csv", include_in_schema=False)
def export_analytics_csv(
    days: int = 30,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    points = _compute_daily_stats(db, days)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["date", "new_users", "new_conversations", "ai_requests", "input_tokens", "output_tokens"]
    )
    for p in points:
        writer.writerow(
            [p.date, p.new_users, p.new_conversations, p.ai_requests, p.input_tokens, p.output_tokens]
        )
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics.csv"},
    )


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    limit: int = 100,
    offset: int = 0,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    return db.query(User).order_by(User.created_at.desc()).offset(offset).limit(limit).all()


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستخدم غير موجود")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    log_event(
        db, "admin_user_updated", f"admin {admin.email} عدّل المستخدم {user.email}: {data}", admin.id
    )
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ما تقدر تحذف حسابك من هنا — استخدم حذف الحساب من صفحتك الشخصية",
        )
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستخدم غير موجود")

    log_event(db, "admin_user_deleted", f"admin {admin.email} حذف المستخدم {user.email}", admin.id)
    shutil.rmtree(Path(app_settings.UPLOAD_DIR) / str(user.id), ignore_errors=True)
    db.delete(user)
    db.commit()


@router.get("/conversations", response_model=list[AdminConversationOut])
def list_all_conversations(
    limit: int = 100,
    offset: int = 0,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    rows = (
        db.query(Conversation, User.email)
        .join(User, Conversation.user_id == User.id)
        .order_by(Conversation.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        AdminConversationOut(
            id=conversation.id,
            user_id=conversation.user_id,
            user_email=email,
            title=conversation.title,
            created_at=conversation.created_at,
        )
        for conversation, email in rows
    ]


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_conversation(
    conversation_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة غير موجودة")

    log_event(
        db,
        "admin_conversation_deleted",
        f"admin {admin.email} حذف محادثة #{conversation_id}",
        admin.id,
    )
    db.delete(conversation)
    db.commit()


@router.get("/logs", response_model=list[AuditLogOut])
def list_audit_logs(
    limit: int = 100,
    offset: int = 0,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
