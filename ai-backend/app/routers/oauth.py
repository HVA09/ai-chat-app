"""OAuth connector management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.oauth_connection import OAuthConnection
from app.models.user import User
from app.schemas.oauth import (
    OAuthCallbackOut,
    OAuthConnectionOut,
    OAuthProviderOut,
    OAuthStartOut,
)
from app.services.oauth_service import (
    OAuthConnectorError,
    begin_oauth,
    complete_oauth,
    configured_providers,
    provider_config,
    refresh_oauth_connection,
)

router = APIRouter(prefix="/oauth", tags=["OAuth Connectors"])


def _get_owned_connection(
    connection_id: int,
    current_user: User,
    db: Session,
) -> OAuthConnection:
    connection = (
        db.query(OAuthConnection)
        .filter(
            OAuthConnection.id == connection_id,
            OAuthConnection.user_id == current_user.id,
        )
        .first()
    )
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth connection غير موجود.",
        )
    return connection


@router.get("/providers", response_model=list[OAuthProviderOut])
def list_oauth_providers():
    return [OAuthProviderOut(provider=name) for name in configured_providers()]


@router.post("/{provider}/start", response_model=OAuthStartOut)
def start_oauth(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        # Validate provider before creating a state row.
        config = provider_config(provider)
        authorization_url, expires_at = begin_oauth(
            config.name,
            current_user.id,
            db,
        )
    except OAuthConnectorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return OAuthStartOut(
        provider=config.name,
        authorization_url=authorization_url,
        expires_at=expires_at,
    )


@router.get("/{provider}/callback", response_model=OAuthCallbackOut)
async def oauth_callback(
    provider: str,
    state: str = Query(min_length=20, max_length=200),
    code: str | None = Query(default=None, min_length=1, max_length=8192),
    error: str | None = Query(default=None, max_length=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth provider returned an error: {error}",
        )
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth authorization code is missing.",
        )

    try:
        connection = await complete_oauth(
            provider,
            current_user.id,
            state,
            code,
            db,
        )
    except OAuthConnectorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return OAuthCallbackOut(
        provider=connection.provider,
        connection_id=connection.id,
        email=connection.email,
    )


@router.get("/connections", response_model=list[OAuthConnectionOut])
def list_oauth_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(OAuthConnection)
        .filter(OAuthConnection.user_id == current_user.id)
        .order_by(OAuthConnection.created_at.desc(), OAuthConnection.id.desc())
        .all()
    )


@router.post(
    "/connections/{connection_id}/refresh",
    response_model=OAuthConnectionOut,
)
async def refresh_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    connection = _get_owned_connection(connection_id, current_user, db)
    try:
        connection = await refresh_oauth_connection(connection, db)
    except OAuthConnectorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return connection


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_oauth_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    connection = _get_owned_connection(connection_id, current_user, db)
    db.delete(connection)
    db.commit()
