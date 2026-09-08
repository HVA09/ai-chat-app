"""
تشفير كلمات المرور، وإنشاء/فك تشفير JWT tokens، وتشفير أسرار TOTP.
"""
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import uuid

from cryptography.fernet import Fernet, InvalidToken
from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_TOTP_PREFIX = "enc:v1:"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, expires_delta: timedelta, token_type: str, jti: str | None = None, token_version: int = 0) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "ver": token_version,
        **({"jti": jti} if jti else {}),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int, token_version: int = 0) -> str:
    return _create_token(str(user_id), timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access", token_version=token_version)


def create_refresh_token(user_id: int, token_version: int = 0) -> str:
    return _create_token(str(user_id), timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh", uuid.uuid4().hex, token_version)


def create_email_verification_token(user_id: int) -> str:
    return _create_token(str(user_id), timedelta(hours=24), "email_verify", uuid.uuid4().hex)


def create_password_reset_token(user_id: int) -> str:
    return _create_token(str(user_id), timedelta(hours=1), "password_reset", uuid.uuid4().hex)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def _totp_fernet() -> Fernet:
    key = settings.TOTP_ENCRYPTION_KEY
    if not key:
        # Development/test fallback is deterministically derived from the JWT secret.
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.JWT_SECRET_KEY.encode()).digest()).decode()
    return Fernet(key.encode())


def encrypt_totp_secret(secret: str) -> str:
    return _TOTP_PREFIX + _totp_fernet().encrypt(secret.encode()).decode()


def decrypt_totp_secret(value: str) -> str:
    if not value.startswith(_TOTP_PREFIX):
        # Backward compatibility for existing installations; new writes are encrypted.
        return value
    try:
        return _totp_fernet().decrypt(value[len(_TOTP_PREFIX):].encode()).decode()
    except InvalidToken as exc:
        raise ValueError("TOTP secret could not be decrypted") from exc
