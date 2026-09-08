"""
مسارات Two Factor Authentication (TOTP) — إعداد، تفعيل، تعطيل
"""
import base64
import io

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.audit import log_event
from app.auth.security import decrypt_totp_secret, encrypt_totp_secret
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import TwoFactorCodeRequest, TwoFactorSetupResponse

router = APIRouter(prefix="/auth/2fa", tags=["Two-Factor Authentication"])


def _qr_code_base64(data: str) -> str:
    img = qrcode.make(data)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def _totp(user: User) -> pyotp.TOTP:
    if not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لازم تسوي /2fa/setup أولًا")
    try:
        return pyotp.TOTP(decrypt_totp_secret(user.totp_secret))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="تعذر قراءة إعدادات 2FA")


@router.post("/setup", response_model=TwoFactorSetupResponse)
def setup_two_factor(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    secret = pyotp.random_base32()
    current_user.totp_secret = encrypt_totp_secret(secret)
    current_user.is_2fa_enabled = False
    current_user.token_version += 1
    db.commit()

    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=current_user.email, issuer_name=settings.TOTP_ISSUER_NAME)
    return TwoFactorSetupResponse(secret=secret, qr_code_base64=_qr_code_base64(provisioning_uri))


@router.post("/enable")
def enable_two_factor(payload: TwoFactorCodeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    totp = _totp(current_user)
    if not totp.verify(payload.totp_code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="رمز التحقق غير صحيح")
    current_user.is_2fa_enabled = True
    current_user.token_version += 1
    db.commit()
    log_event(db, "2fa_enabled", f"تفعيل 2FA: {current_user.email}", current_user.id)
    return {"detail": "تم تفعيل التحقق الثنائي"}


@router.post("/disable")
def disable_two_factor(payload: TwoFactorCodeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_2fa_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="التحقق الثنائي غير مفعّل أصلًا")
    totp = _totp(current_user)
    if not totp.verify(payload.totp_code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="رمز التحقق غير صحيح")

    current_user.is_2fa_enabled = False
    current_user.totp_secret = None
    current_user.token_version += 1
    db.commit()
    log_event(db, "2fa_disabled", f"تعطيل 2FA: {current_user.email}", current_user.id)
    return {"detail": "تم تعطيل التحقق الثنائي"}
