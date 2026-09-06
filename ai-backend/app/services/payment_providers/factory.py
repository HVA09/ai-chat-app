"""
يختار مزوّد الدفع المناسب حسب PAYMENT_PROVIDER في الإعدادات (.env)
"""
from app.config import settings
from app.services.payment_providers.base import PaymentProvider
from app.services.payment_providers.paypal_provider import PayPalProvider
from app.services.payment_providers.stripe_provider import StripeProvider


def get_payment_provider() -> PaymentProvider:
    provider_name = settings.PAYMENT_PROVIDER.lower().strip()

    if provider_name == "stripe":
        return StripeProvider(
            secret_key=settings.STRIPE_SECRET_KEY, webhook_secret=settings.STRIPE_WEBHOOK_SECRET
        )
    if provider_name == "paypal":
        return PayPalProvider(
            client_id=settings.PAYPAL_CLIENT_ID,
            client_secret=settings.PAYPAL_CLIENT_SECRET,
            webhook_id=settings.PAYPAL_WEBHOOK_ID,
            api_base=settings.PAYPAL_API_BASE,
        )
    raise ValueError(f"PAYMENT_PROVIDER='{provider_name}' غير مدعوم — الخيارات: stripe, paypal")
