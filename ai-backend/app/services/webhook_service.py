"""Developer webhook validation, signing, queuing, and delivery."""

from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import httpx
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.config import settings
from app.models.webhook_delivery import WebhookDelivery
from app.models.webhook_endpoint import WebhookEndpoint

MAX_PAYLOAD_BYTES = 64 * 1024
MAX_DELIVERY_ATTEMPTS = 5
RETRY_DELAYS_SECONDS = (5, 30, 300, 900)

SUPPORTED_WEBHOOK_EVENTS = (
    "api_key.created",
    "api_key.revoked",
    "webhook.test",
)


class WebhookValidationError(ValueError):
    """Raised when a developer webhook configuration is unsafe."""


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.JWT_SECRET_KEY.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def generate_webhook_secret() -> str:
    return f"whsec_{secrets.token_urlsafe(32)}"


def encrypt_webhook_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_webhook_secret(secret_encrypted: str) -> str:
    return _fernet().decrypt(secret_encrypted.encode("utf-8")).decode("utf-8")


def _is_public_ip(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_global
    except (TypeError, ValueError):
        return False


def _resolve_public_host(hostname: str) -> list[str]:
    """Resolve once and reject the entire DNS answer set if any address is unsafe."""
    try:
        addresses = sorted({
            item[4][0]
            for item in socket.getaddrinfo(
                hostname,
                None,
                proto=socket.IPPROTO_TCP,
            )
        })
    except (OSError, IndexError, TypeError, ValueError) as exc:
        raise WebhookValidationError("تعذر التحقق من نطاق Webhook.") from exc

    if not addresses or any(not _is_public_ip(address) for address in addresses):
        raise WebhookValidationError(
            "عنوان Webhook يجب أن يشير إلى خادم عام وليس شبكة داخلية."
        )
    return addresses


def _prepare_pinned_webhook_request(url: str) -> tuple[str, str, dict]:
    """Validate URL and pin the connection to a vetted public IP address."""

    value = url.strip()
    if len(value) > 2048:
        raise WebhookValidationError("رابط Webhook طويل جدًا.")

    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        raise WebhookValidationError("رابط Webhook يجب أن يستخدم HTTP أو HTTPS.")
    if settings.ENVIRONMENT == "production" and parsed.scheme != "https":
        raise WebhookValidationError("Webhooks في production يجب أن تستخدم HTTPS.")
    if parsed.username or parsed.password:
        raise WebhookValidationError("رابط Webhook لا يمكن أن يحتوي بيانات دخول.")
    host = parsed.hostname
    if not host:
        raise WebhookValidationError("رابط Webhook غير صالح.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise WebhookValidationError("منفذ Webhook غير صالح.") from exc
    if port is not None and not 1 <= port <= 65535:
        raise WebhookValidationError("منفذ Webhook غير صالح.")

    host = host.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
        raise WebhookValidationError("عناوين localhost غير مسموحة.")
    if host.endswith(".local") or host.endswith(".internal"):
        raise WebhookValidationError("النطاقات الداخلية غير مسموحة.")

    try:
        literal_ip = ipaddress.ip_address(host)
    except ValueError:
        is_ip_literal = False
        try:
            ascii_host = host.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise WebhookValidationError("اسم نطاق Webhook غير صالح.") from exc
        resolved = _resolve_public_host(ascii_host)
        pinned_ip = ipaddress.ip_address(resolved[0])
    else:
        is_ip_literal = True
        if not literal_ip.is_global:
            raise WebhookValidationError("عنوان Webhook يجب أن يكون عامًا.")
        ascii_host = host
        pinned_ip = literal_ip

    default_port = 443 if parsed.scheme == "https" else 80
    host_for_header = f"[{ascii_host}]" if ":" in ascii_host else ascii_host
    host_header = (
        f"{host_for_header}:{port}"
        if port is not None and port != default_port
        else host_for_header
    )
    pinned_host = (
        f"[{pinned_ip.compressed}]"
        if pinned_ip.version == 6
        else pinned_ip.compressed
    )
    pinned_netloc = f"{pinned_host}:{port}" if port is not None else pinned_host
    pinned_url = parsed._replace(
        netloc=pinned_netloc,
        path=parsed.path or "/",
        fragment="",
    ).geturl()
    extensions = (
        {"sni_hostname": ascii_host}
        if parsed.scheme == "https" and not is_ip_literal
        else {}
    )
    return pinned_url, host_header, extensions


def validate_webhook_url(url: str) -> str:
    value = url.strip()
    _prepare_pinned_webhook_request(value)
    return value


def serialize_payload(event_type: str, event_id: str, payload: dict) -> bytes:
    envelope = {
        "id": event_id,
        "type": event_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }
    body = json.dumps(
        envelope,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if len(body) > MAX_PAYLOAD_BYTES:
        raise WebhookValidationError("Payload الخاص بالـWebhook كبير جدًا.")
    return body


def sign_webhook(secret: str, timestamp: int, body: bytes) -> str:
    message = f"{timestamp}.".encode("utf-8") + body
    signature = hmac.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"


def queue_webhook_event(
    db: Session,
    user_id: int,
    event_type: str,
    payload: dict,
    *,
    endpoint_id: int | None = None,
) -> list[int]:
    if event_type not in SUPPORTED_WEBHOOK_EVENTS:
        raise WebhookValidationError("نوع Webhook غير مدعوم.")

    event_id = uuid.uuid4().hex
    serialize_payload(event_type, event_id, payload)

    query = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.user_id == user_id,
        WebhookEndpoint.is_active.is_(True),
    )
    if endpoint_id is not None:
        query = query.filter(WebhookEndpoint.id == endpoint_id)

    endpoints = query.all()
    delivery_ids: list[int] = []
    for endpoint in endpoints:
        if endpoint_id is None and event_type not in (endpoint.event_types or []):
            continue
        delivery = WebhookDelivery(
            webhook_endpoint_id=endpoint.id,
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            status="queued",
            attempt_count=0,
        )
        db.add(delivery)
        db.flush()
        delivery_ids.append(delivery.id)

    return delivery_ids


def enqueue_webhook_deliveries(delivery_ids: list[int]) -> None:
    if not delivery_ids:
        return
    from app.tasks import deliver_webhook_task

    for delivery_id in delivery_ids:
        try:
            deliver_webhook_task.delay(delivery_id)
        except Exception:
            # The persisted queued row is retained for an operator/retry sweep.
            continue


def _retry_delay(attempt_count: int) -> int:
    index = max(0, min(attempt_count - 1, len(RETRY_DELAYS_SECONDS) - 1))
    return RETRY_DELAYS_SECONDS[index]


def _schedule_retry(delivery: WebhookDelivery, db: Session, *, error: str, response_status: int | None) -> bool:
    if delivery.attempt_count >= MAX_DELIVERY_ATTEMPTS:
        delivery.status = "failed"
        delivery.last_error = error[:1000]
        delivery.response_status = response_status
        delivery.next_attempt_at = None
        # Persist the terminal state when an owned worker session closes.
        db.commit()
        return False

    delay = _retry_delay(delivery.attempt_count)
    delivery.status = "queued"
    delivery.last_error = error[:1000]
    delivery.response_status = response_status
    delivery.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
    db.commit()
    return True


def deliver_webhook_delivery(delivery_id: int, db: Session | None = None) -> None:
    from app.database import SessionLocal

    owns_session = db is None
    if db is None:
        db = SessionLocal()

    try:
        delivery = (
            db.query(WebhookDelivery)
            .filter(WebhookDelivery.id == delivery_id)
            .with_for_update()
            .first()
        )
        if delivery is None or delivery.status != "queued":
            return
        if (
            delivery.next_attempt_at is not None
            and delivery.next_attempt_at > datetime.now(timezone.utc)
        ):
            return

        endpoint = db.get(WebhookEndpoint, delivery.webhook_endpoint_id)
        if endpoint is None:
            delivery.status = "failed"
            delivery.last_error = "Webhook endpoint غير موجود."
            delivery.next_attempt_at = None
            db.commit()
            return

        if not endpoint.is_active:
            delivery.status = "cancelled"
            delivery.next_attempt_at = None
            delivery.last_error = "Webhook endpoint معطّل."
            db.commit()
            return

        try:
            url, host_header, request_extensions = _prepare_pinned_webhook_request(
                endpoint.url
            )
            secret = decrypt_webhook_secret(endpoint.secret_encrypted)
            body = serialize_payload(
                delivery.event_type,
                delivery.event_id,
                delivery.payload,
            )
        except WebhookValidationError as exc:
            delivery.status = "failed"
            delivery.last_error = str(exc)[:1000]
            delivery.next_attempt_at = None
            db.commit()
            return
        except Exception as exc:
            delivery.status = "failed"
            delivery.last_error = "تعذر قراءة إعدادات Webhook."
            delivery.next_attempt_at = None
            db.commit()
            return

        delivery.attempt_count += 1
        delivery.status = "sending"
        delivery.last_error = None
        # Keep the row lock and transaction open through the bounded HTTP call.
        # The recovery sweep uses FOR UPDATE SKIP LOCKED and cannot reclaim this
        # delivery while a sender is active. A crashed worker rolls back to queued.

        timestamp = int(datetime.now(timezone.utc).timestamp())
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ai-chat-app-webhook/1.0",
            "X-Webhook-Id": delivery.event_id,
            "X-Webhook-Event": delivery.event_type,
            "X-Webhook-Timestamp": str(timestamp),
            "X-Webhook-Signature": sign_webhook(secret, timestamp, body),
        }

        try:
            with httpx.Client(
                timeout=httpx.Timeout(10.0, connect=5.0),
                follow_redirects=False,
                trust_env=False,
            ) as client:
                headers["Host"] = host_header
                response = client.post(
                    url,
                    content=body,
                    headers=headers,
                    extensions=request_extensions,
                )
        except Exception as exc:
            should_retry = _schedule_retry(
                delivery,
                db,
                error=f"network error: {exc}",
                response_status=None,
            )
            if should_retry:
                from app.tasks import deliver_webhook_task

                deliver_webhook_task.apply_async(
                    args=[delivery.id],
                    countdown=_retry_delay(delivery.attempt_count),
                )
            return

        if 200 <= response.status_code < 300:
            delivery.status = "delivered"
            delivery.response_status = response.status_code
            delivery.last_error = None
            delivery.next_attempt_at = None
            delivery.delivered_at = datetime.now(timezone.utc)
            db.commit()
            return

        retryable = response.status_code in {408, 425, 429} or response.status_code >= 500
        error = f"Webhook endpoint returned HTTP {response.status_code}"
        if retryable and _schedule_retry(
            delivery,
            db,
            error=error,
            response_status=response.status_code,
        ):
            from app.tasks import deliver_webhook_task

            deliver_webhook_task.apply_async(
                args=[delivery.id],
                countdown=_retry_delay(delivery.attempt_count),
            )
            return

        delivery.status = "failed"
        delivery.response_status = response.status_code
        delivery.last_error = error
        delivery.next_attempt_at = None
        db.commit()
    finally:
        if owns_session:
            db.close()
