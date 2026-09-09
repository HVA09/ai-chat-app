"""
مزوّد PayPal — عبر REST API مباشرة (ما فيه SDK رسمي مستقر بديل stripe الرسمية).
يحتاج: الحصول على access token أولًا (OAuth2)، ثم استخدامه بكل طلب.
التحقق من الـ webhook يصير عبر استدعاء PayPal نفسه (verify-webhook-signature)
"""
import json

import httpx

from app.services.payment_providers.base import CheckoutResult, PaymentProvider, WebhookEvent


class PayPalProvider(PaymentProvider):
    def __init__(self, client_id: str, client_secret: str, webhook_id: str, api_base: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.webhook_id = webhook_id
        self.api_base = api_base.rstrip("/")

    async def _get_access_token(self, client: httpx.AsyncClient) -> str:
        response = await client.post(
            f"{self.api_base}/v1/oauth2/token",
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
        )
        response.raise_for_status()
        return response.json()["access_token"]

    async def create_checkout_session(
        self, user_id: int, user_email: str, plan, success_url: str, cancel_url: str
    ) -> CheckoutResult:
        async with httpx.AsyncClient(timeout=30.0) as client:
            token = await self._get_access_token(client)
            response = await client.post(
                f"{self.api_base}/v1/billing/subscriptions",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "plan_id": plan.paypal_plan_id,
                    "custom_id": f"{user_id}:{plan.id}",
                    "subscriber": {"email_address": user_email},
                    "application_context": {
                        "return_url": success_url,
                        "cancel_url": cancel_url,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

        approval_link = next(
            (link["href"] for link in data.get("links", []) if link.get("rel") == "approve"), None
        )
        return CheckoutResult(checkout_url=approval_link)

    async def cancel_subscription(self, provider_subscription_id: str) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            token = await self._get_access_token(client)
            response = await client.post(
                f"{self.api_base}/v1/billing/subscriptions/{provider_subscription_id}/cancel",
                headers={"Authorization": f"Bearer {token}"},
                json={"reason": "طلب المستخدم"},
            )
            response.raise_for_status()

    def verify_webhook(self, payload: bytes, headers: dict[str, str]) -> WebhookEvent:
        # ملاحظة: هذا التحقق يحتاج استدعاء شبكي فعلي لـ PayPal (async)، بعكس Stripe اللي
        # تحققه محلي (HMAC). لأن الواجهة الأساسية sync هنا، الاستدعاء الفعلي يصير
        # بمسار الـ webhook نفسه في routers/billing.py وليس هنا — راجع verify_paypal_webhook_async
        raise NotImplementedError(
            "استخدم verify_paypal_webhook_async في routers/billing.py — PayPal يحتاج استدعاء شبكي"
        )

    async def verify_webhook_async(self, payload: bytes, headers: dict[str, str]) -> WebhookEvent:
        body = json.loads(payload)
        async with httpx.AsyncClient(timeout=30.0) as client:
            token = await self._get_access_token(client)
            verify_response = await client.post(
                f"{self.api_base}/v1/notifications/verify-webhook-signature",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "auth_algo": headers.get("paypal-auth-algo"),
                    "cert_url": headers.get("paypal-cert-url"),
                    "transmission_id": headers.get("paypal-transmission-id"),
                    "transmission_sig": headers.get("paypal-transmission-sig"),
                    "transmission_time": headers.get("paypal-transmission-time"),
                    "webhook_id": self.webhook_id,
                    "webhook_event": body,
                },
            )
            verify_response.raise_for_status()

        if verify_response.json().get("verification_status") != "SUCCESS":
            raise ValueError("توقيع PayPal webhook غير صالح")

        event_type = body.get("event_type", "")
        resource = body.get("resource", {})
        custom_id = resource.get("custom_id") or ""
        user_id_part, _, plan_id_part = custom_id.partition(":")

        if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
            mapped_type, status = "checkout_completed", "active"
        elif event_type == "BILLING.SUBSCRIPTION.CANCELLED":
            mapped_type, status = "subscription_canceled", "canceled"
        elif event_type == "BILLING.SUBSCRIPTION.UPDATED":
            mapped_type, status = "subscription_updated", resource.get("status", "").lower()
        else:
            mapped_type, status = "ignored", None

        return WebhookEvent(
            event_type=mapped_type,
            provider_subscription_id=resource.get("id"),
            provider_customer_id=None,
            status=status,
            client_reference_id=user_id_part or None,
            plan_id=plan_id_part or None,
        )
