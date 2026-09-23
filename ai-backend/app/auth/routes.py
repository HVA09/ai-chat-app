"""
مسارات المصادقة: تسجيل، دخول، تجديد التوكن، تأكيد البريد، وإعادة تعيين كلمة المرور.
"""
from datetime import datetime, timedelta, timezone
import hashlib

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token, create_email_verification_token, create_password_reset_token,
    create_refresh_token, decode_token, decrypt_totp_secret, hash_password, verify_password,
)
from app.audit import log_event
from app.cache import (
    consume_email_verification_token, consume_password_reset_token, consume_refresh_token,
    remember_email_verification_token, remember_password_reset_token, remember_refresh_token,
)
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.logging_config import get_logger
from app.models.user import User, UserRole
from app.models.user_session import UserSession
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.notifications import notify
from app.schemas.auth import EmailVerificationConfirm, LoginRequest, PasswordResetConfirm, PasswordResetRequest, Token
from app.schemas.user import UserCreate, UserOut
from app.schemas.sessions import SessionOut
from app.services.email_service import send_password_reset_email, send_verification_email, send_welcome_email

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger("auth")


def _set_session_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = settings.ENVIRONMENT == "production"
    same_site = "none" if secure else "lax"
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=secure, samesite=same_site, max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, path="/auth")
    response.set_cookie("access_token", access_token, httponly=True, secure=secure, samesite=same_site, max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/")


def _token_response(access_token: str, refresh_token: str) -> Token:
    """Never expose authentication tokens in the JSON response; use HttpOnly cookies."""
    return Token(token_type="bearer")



def _hash_session_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


def _create_session_record(
    *,
    db: Session,
    user: User,
    refresh_token: str,
    request: Request,
    now: datetime,
) -> UserSession:
    data = decode_token(refresh_token, expected_type="refresh")
    jti = data.get("jti")
    if not jti:
        raise HTTPException(status_code=503, detail="تعذر إنشاء جلسة الدخول")
    session = UserSession(
        user_id=user.id,
        jti_hash=_hash_session_jti(jti),
        user_agent=(request.headers.get("user-agent") or "")[:500] or None,
        ip_address=(request.client.host if request.client else None),
        created_at=now,
        last_used_at=now,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    return session


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="البريد مسجل مسبقًا")
    initial_admin = (settings.INITIAL_ADMIN_EMAIL or "").strip().lower()
    is_initial_admin = bool(initial_admin and payload.email.lower() == initial_admin)
    user = User(email=payload.email, hashed_password=hash_password(payload.password), role=UserRole.admin if is_initial_admin else UserRole.user)
    db.add(user)
    db.flush()

    personal_workspace = Workspace(owner_id=user.id, name="Personal")
    db.add(personal_workspace)
    db.flush()
    db.add(
        WorkspaceMember(
            workspace_id=personal_workspace.id,
            user_id=user.id,
            role=WorkspaceRole.owner,
        )
    )

    db.commit()
    db.refresh(user)
    log_event(db, "register", f"مستخدم جديد: {user.email} (admin={is_initial_admin})", user.id)
    token = create_email_verification_token(user.id)
    jti = decode_token(token).get("jti")
    if not jti or not remember_email_verification_token(jti, 24 * 3600):
        raise HTTPException(status_code=503, detail="خدمة التحقق غير متاحة مؤقتًا")
    send_verification_email(user.email, token)
    send_welcome_email(user.email)
    notify(db, user.id, "أهلًا بك", "تم إنشاء حسابك بنجاح.", "welcome")
    return user


@router.post("/login", response_model=Token, response_model_exclude_none=True)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="بريد إلكتروني أو كلمة مرور غير صحيحة")
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise invalid
    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="الحساب مقفل مؤقتًا، حاول لاحقًا")
    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
        db.commit()
        log_event(db, "login_failed", f"محاولة دخول فاشلة: {payload.email}", user.id)
        raise invalid
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="هذا الحساب معطّل. تواصل مع الدعم إن كان هذا خطأ.")
    if user.is_2fa_enabled:
        if not payload.totp_code:
            raise HTTPException(status_code=status.HTTP_428_PRECONDITION_REQUIRED, detail="مطلوب رمز التحقق الثنائي")
        try:
            secret = decrypt_totp_secret(user.totp_secret or "")
        except ValueError:
            raise HTTPException(status_code=500, detail="تعذر قراءة إعدادات 2FA")
        if not pyotp.TOTP(secret).verify(payload.totp_code, valid_window=1):
            log_event(db, "2fa_failed", f"رمز 2FA غير صحيح: {user.email}", user.id)
            raise HTTPException(status_code=401, detail="رمز التحقق الثنائي غير صحيح")
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    refresh_token = create_refresh_token(user.id, user.token_version)
    jti = decode_token(refresh_token).get("jti")
    if not jti or not remember_refresh_token(jti, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400):
        raise HTTPException(status_code=503, detail="خدمة الجلسات غير متاحة مؤقتًا")
    _create_session_record(db=db, user=user, refresh_token=refresh_token, request=request, now=now)
    db.commit()
    access_token = create_access_token(user.id, user.token_version)
    _set_session_cookies(response, access_token, refresh_token)
    log_event(db, "login", f"تسجيل دخول ناجح: {user.email}", user.id)
    return _token_response(access_token, refresh_token)


@router.post("/refresh", response_model=Token, response_model_exclude_none=True)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token غير صالح")
    refresh_token = request.cookies.get("refresh_token")
    logger.debug("refresh_cookie_present=%s", bool(refresh_token))
    try:
        if not refresh_token:
            raise ValueError("missing")
        data = decode_token(refresh_token)
        if data.get("type") != "refresh":
            raise ValueError("wrong type")
        user_id = int(data.get("sub"))
        token_version = int(data.get("ver", -1))
    except (JWTError, TypeError, ValueError):
        logger.debug("refresh_jwt_invalid=True")
        raise invalid
    jti = data.get("jti")
    consumed = bool(jti and consume_refresh_token(jti))
    logger.debug("refresh_jti_present=%s refresh_consume_ok=%s", bool(jti), consumed)
    if not consumed:
        raise invalid
    user = db.get(User, user_id)
    user_valid = user is not None and user.is_active and token_version == user.token_version
    logger.debug("refresh_user_valid=%s", user_valid)
    if not user_valid:
        raise invalid
    now = datetime.now(timezone.utc)
    old_session = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user.id,
            UserSession.jti_hash == _hash_session_jti(jti),
            UserSession.revoked_at.is_(None),
        )
        .first()
    )
    new_refresh_token = create_refresh_token(user.id, user.token_version)
    new_jti = decode_token(new_refresh_token).get("jti")
    if not new_jti or not remember_refresh_token(new_jti, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400):
        raise HTTPException(status_code=503, detail="خدمة الجلسات غير متاحة مؤقتًا")
    if old_session is not None:
        old_session.revoked_at = now
    _create_session_record(db=db, user=user, refresh_token=new_refresh_token, request=request, now=now)
    db.commit()
    new_access_token = create_access_token(user.id, user.token_version)
    _set_session_cookies(response, new_access_token, new_refresh_token)
    return _token_response(new_access_token, new_refresh_token)


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    current_jti = None
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            current_jti = decode_token(refresh_token, expected_type="refresh").get("jti")
        except (JWTError, TypeError, ValueError):
            current_jti = None

    sessions = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == current_user.id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
        .order_by(UserSession.last_used_at.desc(), UserSession.id.desc())
        .all()
    )
    current_hash = _hash_session_jti(current_jti) if current_jti else None
    return [
        SessionOut(
            id=item.id,
            created_at=item.created_at,
            last_used_at=item.last_used_at,
            expires_at=item.expires_at,
            user_agent=item.user_agent,
            ip_address=item.ip_address,
            is_current=item.jti_hash == current_hash,
        )
        for item in sessions
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(UserSession)
        .filter(
            UserSession.id == session_id,
            UserSession.user_id == current_user.id,
            UserSession.revoked_at.is_(None),
        )
        .first()
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الجلسة غير موجودة")
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/sessions/revoke-all", status_code=status.HTTP_204_NO_CONTENT)
def revoke_all_sessions(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.revoked_at.is_(None),
    ).update({UserSession.revoked_at: now}, synchronize_session=False)
    current_user.token_version += 1
    db.commit()
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            data = decode_token(refresh_token)
            jti = data.get("jti")
            if jti:
                consume_refresh_token(jti)
                session = (
                    db.query(UserSession)
                    .filter(
                        UserSession.jti_hash == _hash_session_jti(jti),
                        UserSession.revoked_at.is_(None),
                    )
                    .first()
                )
                if session is not None:
                    session.revoked_at = datetime.now(timezone.utc)
                    db.commit()
        except (JWTError, TypeError, ValueError):
            pass
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/verify-email/request", status_code=status.HTTP_202_ACCEPTED)
def request_email_verification(current_user: User = Depends(get_current_user)):
    if current_user.is_email_verified:
        return {"detail": "البريد مؤكد مسبقًا"}
    token = create_email_verification_token(current_user.id)
    jti = decode_token(token).get("jti")
    if not jti or not remember_email_verification_token(jti, 24 * 3600):
        raise HTTPException(status_code=503, detail="خدمة التحقق غير متاحة مؤقتًا")
    send_verification_email(current_user.email, token)
    return {"detail": "تم إرسال رابط التأكيد"}


@router.post("/verify-email/confirm")
def confirm_email_verification(payload: EmailVerificationConfirm, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=400, detail="رابط التأكيد غير صالح أو منتهي")
    try:
        data = decode_token(payload.token, expected_type="email_verification")
        user_id = int(data.get("sub"))
        jti = data.get("jti")
        if not jti or not consume_email_verification_token(jti):
            raise ValueError
    except (JWTError, TypeError, ValueError):
        raise invalid
    user = db.get(User, user_id)
    if user is None:
        raise invalid
    user.is_email_verified = True
    db.commit()
    log_event(db, "email_verified", f"تم تأكيد بريد: {user.email}", user.id)
    return {"detail": "تم تأكيد البريد الإلكتروني بنجاح"}


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        token = create_password_reset_token(user.id)
        jti = decode_token(token).get("jti")
        if not jti or not remember_password_reset_token(jti, 3600):
            raise HTTPException(status_code=503, detail="خدمة الاستعادة غير متاحة مؤقتًا")
        send_password_reset_email(user.email, token)
    return {"detail": "إذا كان البريد مسجلًا، فسيتم إرسال رابط الاستعادة"}


@router.post("/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=400, detail="رابط الاستعادة غير صالح أو منتهي")
    try:
        data = decode_token(payload.token, expected_type="password_reset")
        user_id = int(data.get("sub"))
        jti = data.get("jti")
        if not jti or not consume_password_reset_token(jti):
            raise ValueError
    except (JWTError, TypeError, ValueError):
        raise invalid
    user = db.get(User, user_id)
    if user is None:
        raise invalid
    user.hashed_password = hash_password(payload.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.token_version += 1
    db.commit()
    log_event(db, "password_reset", f"تم تغيير كلمة المرور: {user.email}", user.id)
    return {"detail": "تم تغيير كلمة المرور بنجاح"}
