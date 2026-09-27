"""OAuth 2.0 connector foundation with PKCE, encrypted tokens, and refresh support."""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.config import settings
from app.models.oauth_connection import OAuthConnection
from app.models.oauth_state import OAuthState


OAUTH_PREFIX = "enc:v1:"


class OAuthConnectorError(ValueError):
    """Safe error raised for OAuth configuration or flow failures."""


@dataclass(frozen=True, slots=True)
class OAuthProviderConfig:
    name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: tuple[str, ...]


def _oauth_fernet() -> Fernet:
    key = settings.TOTP_ENCRYPTION_KEY
    if not key:
        key = base64.urlsafe_b64encode(
            hashlib.sha256(settings.JWT_SECRET_KEY.encode("utf-8")).digest()
        ).decode()
    return Fernet(key.encode())


def encrypt_oauth_secret(value: str) -> str:
    return OAUTH_PREFIX + _oauth_fernet().encrypt(value.encode("utf-8")).decode()


def decrypt_oauth_secret(value: str) -> str:
    if not value.startswith(OAUTH_PREFIX):
        raise OAuthConnectorError("OAuth secret format is invalid.")
    try:
        return _oauth_fernet().decrypt(
            value[len(OAUTH_PREFIX):].encode("utf-8")
        ).decode("utf-8")
    except InvalidToken as exc:
        raise OAuthConnectorError("OAuth secret could not be decrypted.") from exc


def configured_providers() -> tuple[str, ...]:
    names: list[str] = []
    if settings.OAUTH_GOOGLE_CLIENT_ID and settings.OAUTH_GOOGLE_CLIENT_SECRET:
        names.append("google")
    if settings.OAUTH_MICROSOFT_CLIENT_ID and settings.OAUTH_MICROSOFT_CLIENT_SECRET:
        names.append("microsoft")
    return tuple(names)


def provider_config(provider: str) -> OAuthProviderConfig:
    name = provider.strip().lower()

    if name == "google":
        if not (
            settings.OAUTH_GOOGLE_CLIENT_ID
            and settings.OAUTH_GOOGLE_CLIENT_SECRET
        ):
            raise OAuthConnectorError("Google OAuth connector is not configured.")
        return OAuthProviderConfig(
            name="google",
            client_id=settings.OAUTH_GOOGLE_CLIENT_ID,
            client_secret=settings.OAUTH_GOOGLE_CLIENT_SECRET,
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            scopes=("openid", "email", "profile"),
        )

    if name == "microsoft":
        if not (
            settings.OAUTH_MICROSOFT_CLIENT_ID
            and settings.OAUTH_MICROSOFT_CLIENT_SECRET
        ):
            raise OAuthConnectorError(
                "Microsoft OAuth connector is not configured."
            )
        tenant = settings.OAUTH_MICROSOFT_TENANT.strip() or "common"
        base = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0"
        return OAuthProviderConfig(
            name="microsoft",
            client_id=settings.OAUTH_MICROSOFT_CLIENT_ID,
            client_secret=settings.OAUTH_MICROSOFT_CLIENT_SECRET,
            authorize_url=f"{base}/authorize",
            token_url=f"{base}/token",
            userinfo_url=(
                "https://graph.microsoft.com/v1.0/me"
                "?$select=id,displayName,mail,userPrincipalName"
            ),
            scopes=(
                "openid",
                "profile",
                "email",
                "offline_access",
                "User.Read",
            ),
        )

    raise OAuthConnectorError("OAuth provider غير مدعوم.")


def _callback_base() -> str:
    base = settings.OAUTH_CALLBACK_BASE_URL.strip().rstrip("/")
    if not base:
        raise OAuthConnectorError(
            "OAUTH_CALLBACK_BASE_URL is required before enabling OAuth connectors."
        )
    return base


def callback_uri(provider: str) -> str:
    provider_config(provider)
    return f"{_callback_base()}/oauth/{provider.strip().lower()}/callback"


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _hash_state(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def begin_oauth(
    provider: str,
    user_id: int,
    db: Session,
) -> tuple[str, datetime]:
    config = provider_config(provider)
    redirect_uri = callback_uri(provider)

    now = datetime.now(timezone.utc)
    db.query(OAuthState).filter(
        OAuthState.user_id == user_id,
        OAuthState.expires_at < now,
    ).delete(synchronize_session=False)

    state = secrets.token_urlsafe(48)
    verifier, challenge = _pkce_pair()
    expires_at = now + timedelta(seconds=settings.OAUTH_STATE_TTL_SECONDS)

    db.add(
        OAuthState(
            user_id=user_id,
            provider=config.name,
            state_hash=_hash_state(state),
            code_verifier_encrypted=encrypt_oauth_secret(verifier),
            redirect_uri=redirect_uri,
            expires_at=expires_at,
        )
    )
    db.commit()

    params = {
        "client_id": config.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(config.scopes),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }

    if config.name == "google":
        params.update(
            {
                "access_type": "offline",
                "include_granted_scopes": "true",
            }
        )

    return f"{config.authorize_url}?{urlencode(params)}", expires_at


async def _exchange_code(
    config: OAuthProviderConfig,
    code: str,
    verifier: str,
    redirect_uri: str,
) -> dict:
    data = {
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "code": code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
        response = await client.post(
            config.token_url,
            data=data,
            headers={"Accept": "application/json"},
        )

    if response.status_code >= 400:
        raise OAuthConnectorError("OAuth provider rejected the authorization code.")

    try:
        payload = response.json()
    except ValueError as exc:
        raise OAuthConnectorError("OAuth provider returned invalid token data.") from exc

    access_token = payload.get("access_token")
    if not access_token:
        raise OAuthConnectorError("OAuth provider did not return an access token.")

    return payload


async def _fetch_identity(
    config: OAuthProviderConfig,
    access_token: str,
) -> tuple[str, str | None]:
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
        response = await client.get(
            config.userinfo_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )

    if response.status_code >= 400:
        raise OAuthConnectorError("OAuth provider rejected the access token.")

    try:
        payload = response.json()
    except ValueError as exc:
        raise OAuthConnectorError("OAuth provider returned invalid identity data.") from exc

    subject = str(payload.get("sub") or payload.get("id") or "").strip()
    if not subject:
        raise OAuthConnectorError("OAuth provider did not return a stable user id.")

    email = (
        str(
            payload.get("email")
            or payload.get("mail")
            or payload.get("userPrincipalName")
            or ""
        ).strip()
        or None
    )
    return subject, email


async def complete_oauth(
    provider: str,
    user_id: int,
    state: str,
    code: str,
    db: Session,
) -> OAuthConnection:
    config = provider_config(provider)
    now = datetime.now(timezone.utc)
    oauth_state = (
        db.query(OAuthState)
        .filter(
            OAuthState.user_id == user_id,
            OAuthState.provider == config.name,
            OAuthState.state_hash == _hash_state(state),
            OAuthState.used_at.is_(None),
        )
        .first()
    )
    if oauth_state is None or oauth_state.expires_at <= now:
        raise OAuthConnectorError("OAuth state is invalid or expired.")

    verifier = decrypt_oauth_secret(oauth_state.code_verifier_encrypted)
    oauth_state.used_at = now
    db.commit()

    token_payload = await _exchange_code(
        config,
        code,
        verifier,
        oauth_state.redirect_uri,
    )
    access_token = str(token_payload["access_token"])
    refresh_token = token_payload.get("refresh_token")
    subject, email = await _fetch_identity(config, access_token)

    expires_at = None
    expires_in = token_payload.get("expires_in")
    if expires_in is not None:
        try:
            expires_at = now + timedelta(seconds=max(int(expires_in), 0))
        except (TypeError, ValueError):
            expires_at = None

    scopes_raw = str(token_payload.get("scope") or " ".join(config.scopes))
    scopes = [scope for scope in scopes_raw.split() if scope]

    connection = (
        db.query(OAuthConnection)
        .filter(
            OAuthConnection.user_id == user_id,
            OAuthConnection.provider == config.name,
            OAuthConnection.subject == subject,
        )
        .first()
    )
    if connection is None:
        connection = OAuthConnection(
            user_id=user_id,
            provider=config.name,
            subject=subject,
            email=email,
            access_token_encrypted=encrypt_oauth_secret(access_token),
            refresh_token_encrypted=(
                encrypt_oauth_secret(str(refresh_token))
                if refresh_token
                else None
            ),
            token_type=str(token_payload.get("token_type") or "Bearer"),
            scopes=scopes,
            expires_at=expires_at,
        )
        db.add(connection)
    else:
        connection.email = email or connection.email
        connection.access_token_encrypted = encrypt_oauth_secret(access_token)
        if refresh_token:
            connection.refresh_token_encrypted = encrypt_oauth_secret(
                str(refresh_token)
            )
        connection.token_type = str(
            token_payload.get("token_type") or connection.token_type or "Bearer"
        )
        connection.scopes = scopes
        connection.expires_at = expires_at

    db.commit()
    db.refresh(connection)
    return connection


async def refresh_oauth_connection(
    connection: OAuthConnection,
    db: Session,
) -> OAuthConnection:
    config = provider_config(connection.provider)
    if not connection.refresh_token_encrypted:
        raise OAuthConnectorError("هذا الاتصال لا يملك refresh token.")

    refresh_token = decrypt_oauth_secret(connection.refresh_token_encrypted)
    data = {
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
        response = await client.post(
            config.token_url,
            data=data,
            headers={"Accept": "application/json"},
        )

    if response.status_code >= 400:
        raise OAuthConnectorError("تعذر تحديث OAuth token.")

    payload = response.json()
    access_token = str(payload.get("access_token") or "")
    if not access_token:
        raise OAuthConnectorError("موفّر OAuth لم يعد access token جديدًا.")

    connection.access_token_encrypted = encrypt_oauth_secret(access_token)
    if payload.get("refresh_token"):
        connection.refresh_token_encrypted = encrypt_oauth_secret(
            str(payload["refresh_token"])
        )

    expires_in = payload.get("expires_in")
    if expires_in is not None:
        try:
            connection.expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=max(int(expires_in), 0)
            )
        except (TypeError, ValueError):
            pass

    if payload.get("scope"):
        connection.scopes = [
            scope for scope in str(payload["scope"]).split() if scope
        ]

    db.commit()
    db.refresh(connection)
    return connection
