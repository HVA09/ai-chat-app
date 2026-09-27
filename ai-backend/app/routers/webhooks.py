"""Developer Webhook management API."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.webhook_delivery import WebhookDelivery
from app.models.webhook_endpoint import WebhookEndpoint
from app.schemas.webhooks import (
    WebhookCreate,
    WebhookCreatedOut,
    WebhookDeliveryOut,
    WebhookOut,
    WebhookUpdate,
    WebhookUpdateOut,
)
from app.services.webhook_service import (
    WebhookValidationError,
    decrypt_webhook_secret,
    encrypt_webhook_secret,
    generate_webhook_secret,
    enqueue_webhook_deliveries,
    queue_webhook_event,
    validate_webhook_url,
)

router = APIRouter(prefix="/webhooks", tags=["Developer Webhooks"])


def _get_owned_endpoint(endpoint_id: int, current_user: User, db: Session) -> WebhookEndpoint:
    endpoint = (
        db.query(WebhookEndpoint)
        .filter(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.user_id == current_user.id,
        )
        .first()
    )
    if endpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook غير موجود")
    return endpoint


def _public_endpoint(endpoint: WebhookEndpoint) -> WebhookOut:
    return WebhookOut.model_validate(endpoint)


@router.get("", response_model=list[WebhookOut])
def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(WebhookEndpoint)
        .filter(WebhookEndpoint.user_id == current_user.id)
        .order_by(WebhookEndpoint.created_at.desc(), WebhookEndpoint.id.desc())
        .all()
    )


@router.post("", response_model=WebhookCreatedOut, status_code=status.HTTP_201_CREATED)
def create_webhook(
    payload: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        url = validate_webhook_url(payload.url)
    except WebhookValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    secret = generate_webhook_secret()
    endpoint = WebhookEndpoint(
        user_id=current_user.id,
        name=payload.name,
        url=url,
        secret_encrypted=encrypt_webhook_secret(secret),
        event_types=list(payload.event_types),
        is_active=payload.is_active,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    public = WebhookOut.model_validate(endpoint)
    return WebhookCreatedOut(**public.model_dump(), secret=secret)


@router.patch("/{endpoint_id}", response_model=WebhookUpdateOut)
def update_webhook(
    endpoint_id: int,
    payload: WebhookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    endpoint = _get_owned_endpoint(endpoint_id, current_user, db)

    if payload.url is not None:
        try:
            endpoint.url = validate_webhook_url(payload.url)
        except WebhookValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    if payload.name is not None:
        endpoint.name = payload.name
    if payload.event_types is not None:
        endpoint.event_types = list(payload.event_types)
    if payload.is_active is not None:
        endpoint.is_active = payload.is_active

    secret = None
    if payload.rotate_secret:
        secret = generate_webhook_secret()
        endpoint.secret_encrypted = encrypt_webhook_secret(secret)

    db.commit()
    db.refresh(endpoint)
    response = WebhookUpdateOut.model_validate(endpoint)
    return response.model_copy(update={"secret": secret})


@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    endpoint_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    endpoint = _get_owned_endpoint(endpoint_id, current_user, db)
    db.delete(endpoint)
    db.commit()


@router.get("/{endpoint_id}/deliveries", response_model=list[WebhookDeliveryOut])
def list_webhook_deliveries(
    endpoint_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    endpoint = _get_owned_endpoint(endpoint_id, current_user, db)
    return (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.webhook_endpoint_id == endpoint.id)
        .order_by(WebhookDelivery.created_at.desc(), WebhookDelivery.id.desc())
        .limit(100)
        .all()
    )


@router.post("/{endpoint_id}/test", response_model=list[WebhookDeliveryOut], status_code=status.HTTP_202_ACCEPTED)
def test_webhook(
    endpoint_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    endpoint = _get_owned_endpoint(endpoint_id, current_user, db)
    if not endpoint.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Webhook endpoint معطّل")

    delivery_ids = queue_webhook_event(
        db,
        current_user.id,
        "webhook.test",
        {
            "message": "Test webhook from AI Chat App",
            "endpoint_id": endpoint.id,
        },
        endpoint_id=endpoint.id,
    )
    db.commit()
    enqueue_webhook_deliveries(delivery_ids)
    deliveries = db.query(WebhookDelivery).filter(WebhookDelivery.id.in_(delivery_ids)).all()
    return deliveries
