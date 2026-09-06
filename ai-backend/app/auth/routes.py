"""
مسارات المصادقة: تسجيل، دخول (مع حماية Brute Force)، تجديد التوكن،
تأكيد البريد الإلكتروني، وإعادة تعيين كلمة المرور
"""
from datetime import datetime, timedelta, timezone

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token, create_email_verification_token, create_password_reset_token,
    create_refresh_token, decode_token, hash_password, verify_password,
)
from app.audit import log_event
from app.cache import consume_refresh_token, remember_refresh_token
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.notifications import notify
from app.schemas.auth import EmailVerificationConfirm, LoginRequest, PasswordResetConfirm, PasswordResetRequest, RefreshRequest, Token
from app.schemas.user import UserCreate, UserOut
from app.services.email_service import send_password_reset_email, send_verification_email, send_welcome_email

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="البريد مسجل مسبقًا")
    initial_admin = (settings.INITIAL_ADMIN_EMAIL or "").strip().lower()
    is_initial_admin = bool(initial_admin and payload.email.lower() == initial_admin)
    user = User(email=payload.email, hashed_password=hash_password(payload.password), role=UserRole.admin if is_initial_admin else UserRole.user)
    db.add(user); db.commit(); db.refresh(user)
    log_event(db, "register", f"مستخدم جديد: {user.email} (admin={is_initial_admin})", user.id)
    send_verification_email(user.email, create_email_verification_token(user.id))
    send_welcome_email(user.email)
    notify(db, user.id, "أهلًا بك", "تم إنشاء حسابك بنجاح.", "welcome")
    return user

@router.post("/login", response_model=Token)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="بريد إلكتروني أو كلمة مرور غير صحيحة")
    user = db.query(User).filter(User.email == payload.email).first()
    if not user: raise invalid
    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        remaining = int((user.locked_until - now).total_seconds() // 60) + 1
        log_event(db, "login_blocked", f"محاولة دخول لحساب مقفل: {user.email}", user.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"الحساب مقفل مؤقتًا، حاول بعد {remaining} دقيقة")
    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES); db.commit()
            log_event(db, "account_locked", f"تم قفل الحساب مؤقتًا: {user.email}", user.id)
            notify(db, user.id, "قفل الحساب مؤقتًا", "محاولات دخول فاشلة متكررة على حسابك — تم قفله مؤقتًا لحمايتك.", "security")
        else: db.commit()
        log_event(db, "login_failed", f"محاولة دخول فاشلة: {payload.email}", user.id)
        raise invalid
    if not user.is_active:
        log_event(db, "login_inactive", f"محاولة دخول لحساب معطّل: {user.email}", user.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="هذا الحساب معطّل. تواصل مع الدعم إن كان هذا خطأ.")
    if user.is_2fa_enabled:
        if not payload.totp_code: raise HTTPException(status_code=status.HTTP_428_PRECONDITION_REQUIRED, detail="مطلوب رمز التحقق الثنائي")
        if not pyotp.TOTP(user.totp_secret).verify(payload.totp_code, valid_window=1):
            log_event(db, "2fa_failed", f"رمز 2FA غير صحيح: {user.email}", user.id)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="رمز التحقق الثنائي غير صحيح")
    if user.failed_login_attempts or user.locked_until:
        user.failed_login_attempts = 0; user.locked_until = None; db.commit()
    log_event(db, "login", f"تسجيل دخول: {user.email}", user.id)
    refresh_token = create_refresh_token(user.id); jti = decode_token(refresh_token).get("jti")
    if not jti or not remember_refresh_token(jti, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400): raise HTTPException(status_code=503, detail="خدمة الجلسات غير متاحة مؤقتًا")
    access_token = create_access_token(user.id); secure = settings.ENVIRONMENT == "production"
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=secure, samesite="lax", max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, path="/auth")
    response.set_cookie("access_token", access_token, httponly=True, secure=secure, samesite="lax", max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/")
    return Token(access_token=access_token)

@router.post("/refresh", response_model=Token)
def refresh(payload: RefreshRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token غير صالح")
    try:
        token = payload.refresh_token or request.cookies.get("refresh_token")
        data = decode_token(token) if token else None
        if not data or data.get("type") != "refresh": raise ValueError
        user_id = int(data.get("sub"))
    except (JWTError, TypeError, ValueError): raise invalid
    jti = data.get("jti")
    if not jti or not consume_refresh_token(jti): raise invalid
    user = db.get(User, user_id)
    if user is None or not user.is_active: raise invalid
    new_refresh = create_refresh_token(user.id); new_jti = decode_token(new_refresh).get("jti")
    if not new_jti or not remember_refresh_token(new_jti, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400): raise HTTPException(status_code=503, detail="خدمة الجلسات غير متاحة مؤقتًا")
    new_access = create_access_token(user.id); secure = settings.ENVIRONMENT == "production"
    response.set_cookie("refresh_token", new_refresh, httponly=True, secure=secure, samesite="lax", max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, path="/auth")
    response.set_cookie("access_token", new_access, httponly=True, secure=secure, samesite="lax", max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/")
    return Token(access_token=new_access)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if token:
        try:
            data = decode_token(token); jti = data.get("jti")
            if jti: consume_refresh_token(jti)
        except Exception: pass
    response.delete_cookie("refresh_token", path="/auth"); response.delete_cookie("access_token", path="/")

@router.post("/verify-email/request", status_code=status.HTTP_202_ACCEPTED)
def request_email_verification(current_user: User = Depends(get_current_user)):
    if current_user.is_email_verified: return {"detail": "البريد مؤكد مسبقًا"}
    send_verification_email(current_user.email, create_email_verification_token(current_user.id)); return {"detail": "تم إرسال رابط التأكيد"}

@router.post("/verify-email/confirm")
def confirm_email_verification(payload: EmailVerificationConfirm, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رابط التأكيد غير صالح أو منتهي")
    try:
        data = decode_token(payload.token)
        if data.get("type") != "email_verify": raise ValueError
        user_id = int(data.get("sub"))
    except (JWTError, TypeError, ValueError): raise invalid
    user = db.get(User, user_id)
    if user is None: raise invalid
    user.is_email_verified = True; db.commit(); log_event(db, "email_verified", f"تم تأكيد بريد: {user.email}", user.id)
    return {"detail": "تم تأكيد البريد الإلكتروني بنجاح"}

@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        send_password_reset_email(user.email, create_password_reset_token(user.id)); log_event(db, "password_reset_requested", f"طلب إعادة تعيين: {user.email}", user.id)
    return {"detail": "لو البريد مسجّل عندنا، وصلته رسالة بخطوات إعادة التعيين"}

@router.post("/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رابط إعادة التعيين غير صالح أو منتهي")
    try:
        data = decode_token(payload.token)
        if data.get("type") != "password_reset": raise ValueError
        user_id = int(data.get("sub"))
    except (JWTError, TypeError, ValueError): raise invalid
    user = db.get(User, user_id)
    if user is None: raise invalid
    user.hashed_password = hash_password(payload.new_password); user.failed_login_attempts = 0; user.locked_until = None
    db.commit(); log_event(db, "password_reset", f"تم إعادة تعيين كلمة المرور: {user.email}", user.id)
    return {"detail": "تم تغيير كلمة المرور بنجاح"}
