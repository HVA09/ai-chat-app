"""
الواجهة الأساسية لأي مزوّد دفع — Stripe وPayPal يطبّقون نفس الواجهة
عشان routers/billing.py ما يهتم بأي مزوّد يشتغل خلفها
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CheckoutResult:
    checkout_url: str


@dataclass
class WebhookEvent:
    """تمثيل موحّد لحدث webhook — نفس الشكل بغض النظر عن المزوّد"""

    event_type: str  # "checkout_completed" | "subscription_updated" | "subscription_canceled"
    provider_subscription_id: str | None
    provider_customer_id: str | None
    status: str | None  # active | past_due | canceled ...
    client_reference_id: str | None  # user_id مررناه وقت الإنشاء
    plan_id: str | None = None  # الخطة (Plan.id عندنا) اللي مررناها وقت الإنشاء


class PaymentProvider(ABC):
    @abstractmethod
    async def create_checkout_session(
        self, user_id: int, user_email: str, plan, success_url: str, cancel_url: str
    ) -> CheckoutResult:
        raise NotImplementedError

    @abstractmethod
    async def cancel_subscription(self, provider_subscription_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(self, payload: bytes, headers: dict[str, str]) -> WebhookEvent:
        raise NotImplementedError
