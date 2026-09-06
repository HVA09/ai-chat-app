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

logger = get_logger("dependencies")

# tokenUrl هنا لأغراض توثيق Swagger فقط — الدخول الفعلي عبر /auth/login بصيغة JSON
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Authentication: يتحقق من صلاحية JWT ويرجّع المستخدم صاحب التوكن"""
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
    except (JWTError, TypeError, ValueError):
        raise credentials_error

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Authorization: يسمح فقط لمستخدم بدور admin"""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذا الإجراء يتطلب صلاحية admin",
        )
    return current_user


def _daily_ai_limit_for(current_user: User, db: Session) -> int:
    """يرجّع الحد اليومي حسب خطة اشتراك المستخدم — الإعداد الافتراضي لو ما عنده اشتراك فعّال"""
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.active,
        )
        .first()
    )
    if subscription and subscription.plan:
        return subscription.plan.daily_ai_request_limit
    return settings.DAILY_AI_REQUEST_LIMIT


def enforce_daily_ai_limit(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Authorization: يمنع تجاوز الحد اليومي لطلبات AI (حسب خطة الاشتراك) — admin مستثنى"""
    if current_user.role == UserRole.admin:
        return current_user

    daily_limit = _daily_ai_limit_for(current_user, db)
    since = datetime.now(timezone.utc) - timedelta(days=1)
    count = (
        db.query(func.count(UsageLog.id))
        .filter(UsageLog.user_id == current_user.id, UsageLog.created_at >= since)
        .scalar()
    )
    if count >= daily_limit:
        logger.warning("تجاوز الحد اليومي: %s", current_user.email)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"وصلت للحد اليومي المسموح ({daily_limit} طلب) — يمكنك ترقية خطتك لحد أعلى",
        )
    return current_user
