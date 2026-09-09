"""
مزوّد Stripe — يستخدم مكتبة stripe الرسمية (خصوصًا للتحقق الآمن من توقيع الـ webhook)
الاستيراد داخل الدوال (lazy) مو أعلى الملف، عشان باقي التطبيق يشتغل حتى قبل ما تثبّت
مكتبة stripe (لو مو مستخدمها أصلًا).
"""
from app.services.payment_providers.base import CheckoutResult, PaymentProvider, WebhookEvent


class StripeProvider(PaymentProvider):
    def __init__(self, secret_key: str, webhook_secret: str):
        import stripe

        self.webhook_secret = webhook_secret
        stripe.api_key = secret_key

    async def create_checkout_session(
        self, user_id: int, user_email: str, plan, success_url: str, cancel_url: str
    ) -> CheckoutResult:
        import stripe

        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=cancel_url,
            customer_email=user_email,
            client_reference_id=str(user_id),
            metadata={"plan_id": str(plan.id)},
        )
        return CheckoutResult(checkout_url=session.url)

    async def cancel_subscription(self, provider_subscription_id: str) -> None:
        import stripe

        stripe.Subscription.delete(provider_subscription_id)

    def verify_webhook(self, payload: bytes, headers: dict[str, str]) -> WebhookEvent:
        import stripe

        event = stripe.Webhook.construct_event(
            payload, headers.get("stripe-signature", ""), self.webhook_secret
        )
        data = event["data"]["object"]
        stripe_type = event["type"]

        if stripe_type == "checkout.session.completed":
            return WebhookEvent(
                event_type="checkout_completed",
                provider_subscription_id=data.get("subscription"),
                provider_customer_id=data.get("customer"),
                status="active",
                client_reference_id=data.get("client_reference_id"),
                plan_id=(data.get("metadata") or {}).get("plan_id"),
            )
        if stripe_type == "customer.subscription.updated":
            return WebhookEvent(
                event_type="subscription_updated",
                provider_subscription_id=data.get("id"),
                provider_customer_id=data.get("customer"),
                status=data.get("status"),
                client_reference_id=None,
            )
        if stripe_type == "customer.subscription.deleted":
            return WebhookEvent(
                event_type="subscription_canceled",
                provider_subscription_id=data.get("id"),
                provider_customer_id=data.get("customer"),
                status="canceled",
                client_reference_id=None,
            )
        return WebhookEvent(
            event_type="ignored",
            provider_subscription_id=None,
            provider_customer_id=None,
            status=None,
            client_reference_id=None,
        )
