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
from app.cache import cache_delete, cache_get, cache_set
from app.config import settings as app_settings
from app.services.ai_cost import estimate_cost_usd
from app.database import get_db
from app.dependencies import require_admin
from app.models.audit_log import AuditLog
from app.models.plan import Plan
from app.models.conversation import Conversation, Message
from app.models.file_attachment import FileAttachment
from app.models.usage_log import UsageLog
from app.models.user import User
from app.schemas.admin import (
    AdminConversationOut,
    AdminPlanOut,
    AdminPlanUpdate,
    AdminStats,
    AdminUserOut,
    AdminUserUpdate,
    AuditLogOut,
    DailyStatsPoint,
    CostUsageStat,
    CostBudgetStatus,
    FeedbackAnalytics,
    ModelUsageStat,
    ProviderUsageStat,
    ProviderLatencyStat,
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


@router.get("/analytics/latency", response_model=list[ProviderLatencyStat])
def get_provider_latency(
    days: int = 30,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    days = max(1, min(days, 365))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        db.query(
            UsageLog.provider,
            func.count(UsageLog.id),
            func.avg(UsageLog.latency_ms),
            func.min(UsageLog.latency_ms),
            func.max(UsageLog.latency_ms),
        )
        .filter(
            UsageLog.created_at >= since,
            UsageLog.provider.is_not(None),
            UsageLog.latency_ms.is_not(None),
        )
        .group_by(UsageLog.provider)
        .order_by(func.avg(UsageLog.latency_ms).asc(), UsageLog.provider.asc())
        .all()
    )
    return [
        ProviderLatencyStat(
            provider=provider,
            requests=requests,
            avg_latency_ms=round(avg_latency),
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
        )
        for provider, requests, avg_latency, min_latency, max_latency in rows
    ]


@router.get("/analytics/providers", response_model=list[ProviderUsageStat])
def get_provider_usage(
    days: int = 30,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    days = max(1, min(days, 365))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        db.query(
            UsageLog.provider,
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.input_tokens), 0),
            func.coalesce(func.sum(UsageLog.output_tokens), 0),
        )
        .filter(
            UsageLog.created_at >= since,
            UsageLog.provider.is_not(None),
        )
        .group_by(UsageLog.provider)
        .order_by(func.count(UsageLog.id).desc(), UsageLog.provider.asc())
        .all()
    )
    return [
        ProviderUsageStat(
            provider=provider,
            requests=requests,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=(input_tokens or 0) + (output_tokens or 0),
        )
        for provider, requests, input_tokens, output_tokens in rows
    ]


@router.get("/analytics/models", response_model=list[ModelUsageStat])
def get_model_usage(
    days: int = 30,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    days = max(1, min(days, 365))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        db.query(
            UsageLog.model,
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.input_tokens), 0),
            func.coalesce(func.sum(UsageLog.output_tokens), 0),
        )
        .filter(
            UsageLog.created_at >= since,
            UsageLog.model.is_not(None),
        )
        .group_by(UsageLog.model)
        .order_by(func.count(UsageLog.id).desc(), UsageLog.model.asc())
        .all()
    )
    return [
        ModelUsageStat(
            model=model,
            requests=requests,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=(input_tokens or 0) + (output_tokens or 0),
        )
        for model, requests, input_tokens, output_tokens in rows
    ]


@router.get("/analytics/cost", response_model=list[CostUsageStat])
def get_cost_usage(
    days: int = 30,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    days = max(1, min(days, 365))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        db.query(
            UsageLog.provider,
            UsageLog.model,
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.input_tokens), 0),
            func.coalesce(func.sum(UsageLog.output_tokens), 0),
        )
        .filter(
            UsageLog.created_at >= since,
            UsageLog.provider.is_not(None),
            UsageLog.model.is_not(None),
        )
        .group_by(UsageLog.provider, UsageLog.model)
        .order_by(func.count(UsageLog.id).desc(), UsageLog.provider.asc(), UsageLog.model.asc())
        .all()
    )

    results = []
    for provider, model, requests, input_tokens, output_tokens in rows:
        input_cost, output_cost, total_cost = estimate_cost_usd(
            provider, model, input_tokens, output_tokens
        )
        results.append(
            CostUsageStat(
                provider=provider,
                model=model,
                requests=requests,
                input_tokens=input_tokens or 0,
                output_tokens=output_tokens or 0,
                total_tokens=(input_tokens or 0) + (output_tokens or 0),
                input_cost_usd=input_cost,
                output_cost_usd=output_cost,
                total_cost_usd=total_cost,
                pricing_configured=total_cost is not None,
            )
        )
    return results


def _cost_totals_since(db: Session, since: datetime) -> tuple[float, int, bool]:
    rows = (
        db.query(
            UsageLog.provider,
            UsageLog.model,
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.input_tokens), 0),
            func.coalesce(func.sum(UsageLog.output_tokens), 0),
        )
        .filter(
            UsageLog.created_at >= since,
            UsageLog.provider.is_not(None),
            UsageLog.model.is_not(None),
        )
        .group_by(UsageLog.provider, UsageLog.model)
        .all()
    )

    spent = 0.0
    unpriced_requests = 0
    priced_any = False
    for provider, model, requests, input_tokens, output_tokens in rows:
        _, _, total_cost = estimate_cost_usd(
            provider, model, input_tokens, output_tokens
        )
        if total_cost is None:
            unpriced_requests += requests
            continue
        priced_any = True
        spent += total_cost
    return spent, unpriced_requests, priced_any


@router.get("/analytics/budget", response_model=CostBudgetStatus)
def get_cost_budget(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    month_start_dt = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    spent, unpriced_requests, priced_any = _cost_totals_since(db, month_start_dt)

    budget = float(app_settings.AI_MONTHLY_BUDGET_USD or 0)
    budget_usd = budget if budget > 0 else None
    remaining = max(budget - spent, 0.0) if budget_usd is not None else None
    usage_percent = round((spent / budget) * 100, 1) if budget_usd is not None else None

    return CostBudgetStatus(
        month_start=month_start_dt.date().isoformat(),
        budget_usd=budget_usd,
        spent_usd=spent,
        remaining_usd=remaining,
        usage_percent=usage_percent,
        over_budget=budget_usd is not None and spent >= budget,
        pricing_configured=priced_any,
        unpriced_requests=unpriced_requests,
    )


@router.get("/analytics/feedback", response_model=FeedbackAnalytics)
def get_feedback_analytics(
    days: int = 30,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    days = max(1, min(days, 365))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    positive = (
        db.query(func.count(Message.id))
        .filter(
            Message.created_at >= since,
            Message.role == "assistant",
            Message.feedback == 1,
        )
        .scalar()
        or 0
    )
    negative = (
        db.query(func.count(Message.id))
        .filter(
            Message.created_at >= since,
            Message.role == "assistant",
            Message.feedback == -1,
        )
        .scalar()
        or 0
    )
    total_rated = positive + negative
    positive_rate = round((positive / total_rated) * 100, 1) if total_rated else None

    return FeedbackAnalytics(
        days=days,
        total_rated=total_rated,
        positive=positive,
        negative=negative,
        positive_rate=positive_rate,
    )


@router.get("/plans", response_model=list[AdminPlanOut])
def list_plans(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(Plan).order_by(Plan.price_cents.asc(), Plan.id.asc()).all()


@router.patch("/plans/{plan_id}", response_model=AdminPlanOut)
def update_plan(
    plan_id: int,
    payload: AdminPlanUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الخطة غير موجودة",
        )

    data = payload.model_dump(exclude_unset=True)
    if "daily_ai_request_limit" in data and data["daily_ai_request_limit"] is not None:
        if data["daily_ai_request_limit"] < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="حد طلبات AI يجب أن يكون أكبر من صفر",
            )
    if "allowed_models" in data and data["allowed_models"] is not None:
        models = []
        for model in data["allowed_models"]:
            normalized = model.strip()
            if normalized and normalized not in models:
                models.append(normalized)
        data["allowed_models"] = models

    for field, value in data.items():
        setattr(plan, field, value)

    db.commit()
    db.refresh(plan)
    cache_delete("billing:plans:v2")
    log_event(
        db,
        "admin_plan_updated",
        f"admin {admin.email} عدّل الخطة {plan.name}: {data}",
        admin.id,
    )
    return plan


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
