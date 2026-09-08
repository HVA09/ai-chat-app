"""
مسارات المصادقة: تسجيل، دخول، تجديد التوكن، تأكيد البريد، وإعادة تعيين كلمة المرور.
"""
from datetime import datetime, timedelta, timezone

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
from app.models.user import User, UserRole
from app.notifications import notify
from app.schemas.auth import EmailVerificationConfirm, LoginRequest, PasswordResetConfirm, PasswordResetRequest, Token
from app.schemas.user import UserCreate, UserOut
from app.services.email_service import send_password_reset_email, send_verification_email, send_welcome_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_session_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = settings.ENVIRONMENT == "production"
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=secure, samesite="lax", max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, path="/auth")
    response.set_cookie("access_token", access_token, httponly=True, secure=secure, samesite="lax", max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/")


def _token_response(access_token: str, refresh_token: str) -> Token:
    """Return tokens only to the isolated test environment; production uses HttpOnly cookies."""
    if settings.ENVIRONMENT == "test":
        return Token(access_token=access_token, refresh_token=refresh_token)
    return Token(access_token="", refresh_token="")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="البريد مسجل مسبقًا")
    initial_admin = (settings.INITIAL_ADMIN_EMAIL or "").strip().lower()
    is_initial_admin = bool(initial_admin and payload.email.lower() == initial_admin)
    user = User(email=payload.email, hashed_password=hash_password(payload.password), role=UserRole.admin if is_initial_admin else UserRole.user)
    db.add(user)
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


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
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
    access_token = create_access_token(user.id, user.token_version)
    _set_session_cookies(response, access_token, refresh_token)
    return _token_response(access_token, refresh_token)


@router.post("/refresh", response_model=Token)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token غير صالح")
    try:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise ValueError("missing")
        data = decode_token(refresh_token)
        if data.get("type") != "refresh":
            raise ValueError("wrong type")
        user_id = int(data.get("sub"))
        token_version = int(data.get("ver", -1))
    except (JWTError, TypeError, ValueError):
        raise invalid
    jti = data.get("jti")
    if not jti or not consume_refresh_token(jti):
        raise invalid
    user = db.get(User, user_id)
    if user is None or not user.is_active or token_version != user.token_version:
        raise invalid
    new_refresh_token = create_refresh_token(user.id, user.token_version)
    new_jti = decode_token(new_refresh_token).get("jti")
    if not new_jti or not remember_refresh_token(new_jti, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400):
        raise HTTPException(status_code=503, detail="خدمة الجلسات غير متاحة مؤقتًا")
    new_access_token = create_access_token(user.id, user.token_version)
    _set_session_cookies(response, new_access_token, new_refresh_token)
    return _token_response(new_access_token, new_refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            data = decode_token(refresh_token)
            jti = data.get("jti")
            if jti:
                consume_refresh_token(jti)
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
        data = decode_token(payload.token)
        if data.get("type") != "email_verify":
            raise ValueError
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
        data = decode_token(payload.token)
        if data.get("type") != "password_reset":
            raise ValueError
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
