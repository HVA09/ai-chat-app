"""
Dependencies مشتركة بين المسارات: المستخدم الحالي، صلاحية admin، والحد اليومي لطلبات AI
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.config import settings
from app.database import get_db
from app.logging_config import get_logger
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.usage_log import UsageLog
from app.models.user import User, UserRole
from app.models.workspace import Workspace, WorkspaceMember

logger = get_logger("dependencies")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Authentication: يتحقق من JWT ومن رقم إصدار جلسة المستخدم."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="بيانات الدخول غير صالحة",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = token or request.cookies.get("access_token")
        if not token:
            raise ValueError("missing credentials")
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_error
        user_id = int(payload.get("sub"))
        token_version = int(payload.get("ver", -1))
    except (JWTError, TypeError, ValueError):
        raise credentials_error

    user = db.get(User, user_id)
    if user is None or not user.is_active or token_version != user.token_version:
        raise credentials_error
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="هذا الإجراء يتطلب صلاحية admin")
    return current_user


def get_active_subscription_plan(current_user: User, db: Session):
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.active,
        )
        .first()
    )
    return subscription.plan if subscription else None


def get_allowed_ai_models(current_user: User, db: Session) -> list[str]:
    """Return the models this user may select, after global and plan-level policy."""
    global_models = list(settings.AI_ALLOWED_MODELS or [settings.AI_MODEL])
    if current_user.role == UserRole.admin:
        return global_models

    plan = get_active_subscription_plan(current_user, db)
    plan_models = getattr(plan, "allowed_models", None) if plan is not None else None
    if not plan_models:
        return [settings.AI_MODEL] if settings.AI_MODEL in global_models else global_models[:1]
    if "*" in plan_models:
        return global_models

    allowed = [model for model in global_models if model in set(plan_models)]
    return allowed or ([settings.AI_MODEL] if settings.AI_MODEL in global_models else global_models[:1])


def get_daily_ai_limit(current_user: User, db: Session) -> int:
    plan = get_active_subscription_plan(current_user, db)
    if plan is not None:
        return plan.daily_ai_request_limit
    return settings.DAILY_AI_REQUEST_LIMIT


def enforce_daily_ai_limit(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    if current_user.role == UserRole.admin:
        return current_user
    daily_limit = get_daily_ai_limit(current_user, db)
    since = datetime.now(timezone.utc) - timedelta(days=1)
    count = db.query(func.count(UsageLog.id)).filter(
        UsageLog.user_id == current_user.id, UsageLog.created_at >= since
    ).scalar()
    if count >= daily_limit:
        logger.warning("تجاوز الحد اليومي: %s", current_user.email)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"وصلت للحد اليومي المسموح ({daily_limit} طلب) — يمكنك ترقية خطتك لحد أعلى",
        )
    return enforce_ai_cost_budget(current_user, db)


def enforce_ai_cost_budget(
    current_user: User,
    db: Session,
) -> User:
    """يمنع المستخدمين غير الإداريين من بدء طلبات AI بعد تجاوز ميزانية الشهر."""
    budget = float(settings.AI_MONTHLY_BUDGET_USD or 0)
    if budget <= 0 or current_user.role == UserRole.admin:
        return current_user

    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    rows = (
        db.query(
            UsageLog.provider,
            UsageLog.model,
            func.coalesce(func.sum(UsageLog.input_tokens), 0),
            func.coalesce(func.sum(UsageLog.output_tokens), 0),
        )
        .filter(
            UsageLog.created_at >= month_start,
            UsageLog.provider.is_not(None),
            UsageLog.model.is_not(None),
        )
        .group_by(UsageLog.provider, UsageLog.model)
        .all()
    )

    from app.services.ai_cost import estimate_cost_usd

    spent = 0.0
    priced_any = False
    for provider, model, input_tokens, output_tokens in rows:
        _, _, total_cost = estimate_cost_usd(
            provider,
            model,
            int(input_tokens or 0),
            int(output_tokens or 0),
        )
        if total_cost is None:
            continue
        priced_any = True
        spent += total_cost

    if not priced_any:
        return current_user

    if spent >= budget:
        remaining = max(budget - spent, 0.0)
        logger.warning(
            "AI monthly budget exceeded: user=%s spent=%.4f budget=%.4f",
            current_user.email,
            spent,
            budget,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"تم تجاوز ميزانية AI الشهرية المهيأة ({budget:.2f} USD). "
                f"المتبقي: {remaining:.2f} USD."
            ),
        )

    return current_user


def enforce_workspace_daily_ai_limit(
    workspace_id: int,
    current_user: User,
    db: Session,
) -> None:
    """يطبق حد الطلبات اليومي الاختياري لمساحة العمل."""
    if current_user.role == UserRole.admin:
        return

    workspace = (
        db.query(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .filter(
            Workspace.id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
        .first()
    )
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مساحة العمل غير موجودة",
        )

    limit = workspace.daily_ai_request_limit
    if limit is None:
        return

    since = datetime.now(timezone.utc) - timedelta(days=1)
    used = (
        db.query(func.count(UsageLog.id))
        .filter(
            UsageLog.workspace_id == workspace_id,
            UsageLog.created_at >= since,
        )
        .scalar()
        or 0
    )
    if used >= limit:
        logger.warning(
            "تجاوز حد مساحة العمل: workspace_id=%s user=%s",
            workspace_id,
            current_user.email,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"تم الوصول إلى حد مساحة العمل اليومي ({limit} طلب).",
        )
