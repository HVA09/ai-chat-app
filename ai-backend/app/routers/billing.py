"""
مسارات الاشتراكات والدفع: عرض الخطط، بدء الدفع، إلغاء الاشتراك، واستقبال webhooks
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.audit import log_event
from app.cache import cache_get, cache_set
from app.config import settings as app_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.logging_config import get_logger
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.notifications import notify_realtime
from app.schemas.billing import CheckoutRequest, CheckoutResponse, PlanOut, SubscriptionOut
from app.services.email_service import send_subscription_activated_email, send_subscription_canceled_email
from app.services.payment_providers.factory import get_payment_provider
from app.services.payment_providers.paypal_provider import PayPalProvider

router = APIRouter(prefix="/billing", tags=["Billing"])
logger = get_logger("billing")


@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    cache_key = "billing:plans"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    plans = db.query(Plan).filter(Plan.is_active.is_(True)).order_by(Plan.price_cents).all()
    result = [PlanOut.model_validate(p).model_dump() for p in plans]
    cache_set(cache_key, result, app_settings.CACHE_TTL_SECONDS)
    return result


@router.get("/subscription", response_model=SubscriptionOut | None)
def get_my_subscription(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.query(Subscription).filter(Subscription.user_id == current_user.id).first()


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.get(Plan, payload.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الخطة غير موجودة")

    existing = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if existing and existing.status in {
        SubscriptionStatus.incomplete, SubscriptionStatus.trialing, SubscriptionStatus.active, SubscriptionStatus.past_due
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="لديك اشتراك أو عملية دفع قائمة بالفعل")

    success_url = app_settings.FRONTEND_URL.rstrip("/") + app_settings.BILLING_SUCCESS_PATH
    cancel_url = app_settings.FRONTEND_URL.rstrip("/") + app_settings.BILLING_CANCEL_PATH

    provider = get_payment_provider()
    try:
        result = await provider.create_checkout_session(
            user_id=current_user.id,
            user_email=current_user.email,
            plan=plan,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except Exception as exc:
        logger.exception("فشل إنشاء جلسة دفع للمستخدم %s", current_user.email)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="تعذر بدء عملية الدفع"
        ) from exc

    if not result.checkout_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="لم يصل رابط دفع من مزوّد الدفع"
        )
    return CheckoutResponse(checkout_url=result.checkout_url)


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="لا يوجد اشتراك")

    provider = get_payment_provider()
    try:
        await provider.cancel_subscription(subscription.provider_subscription_id)
    except Exception as exc:
        logger.exception("فشل إلغاء اشتراك %s", subscription.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="تعذر إلغاء الاشتراك عند المزوّد"
        ) from exc

    subscription.status = SubscriptionStatus.canceled
    db.commit()
    log_event(db, "subscription_canceled", f"إلغاء اشتراك: {current_user.email}", current_user.id)
    send_subscription_canceled_email(current_user.email)
    await notify_realtime(
        db, current_user.id, "تم إلغاء اشتراكك", "رجعت لحدود الخطة المجانية.", "billing"
    )
    return {"detail": "تم إلغاء الاشتراك"}


async def _apply_webhook_event(event, provider_name: str, db: Session) -> None:
    if event.event_type == "checkout_completed" and event.client_reference_id and event.plan_id:
        user_id = int(event.client_reference_id)
        plan_id = int(event.plan_id)

        existing = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if existing:
            existing.plan_id = plan_id
            existing.provider = provider_name
            existing.provider_subscription_id = event.provider_subscription_id
            existing.provider_customer_id = event.provider_customer_id
            existing.status = SubscriptionStatus.active
        else:
            db.add(
                Subscription(
                    user_id=user_id,
                    plan_id=plan_id,
                    provider=provider_name,
                    provider_subscription_id=event.provider_subscription_id,
                    provider_customer_id=event.provider_customer_id,
                    status=SubscriptionStatus.active,
                )
            )
        db.commit()
        log_event(db, "subscription_activated", f"تفعيل اشتراك عبر {provider_name}", user_id)

        plan = db.get(Plan, plan_id)
        user = db.get(User, user_id)
        if plan and user:
            send_subscription_activated_email(user.email, plan.name)
            await notify_realtime(
                db, user_id, "تم تفعيل اشتراكك", f"خطتك الحالية الآن: {plan.name}", "billing"
            )

    elif event.event_type in ("subscription_updated", "subscription_canceled"):
        subscription = (
            db.query(Subscription)
            .filter(Subscription.provider_subscription_id == event.provider_subscription_id)
            .first()
        )
        if subscription and event.status:
            try:
                subscription.status = SubscriptionStatus(event.status)
            except ValueError:
                pass  # حالة غير معروفة من المزوّد — نتجاهلها بدل ما نفشل الـ webhook كامل
            db.commit()
            log_event(
                db,
                "subscription_status_changed",
                f"اشتراك #{subscription.id} صار: {event.status}",
                subscription.user_id,
            )
            if subscription.status == SubscriptionStatus.canceled:
                user = db.get(User, subscription.user_id)
                if user:
                    send_subscription_canceled_email(user.email)
                    await notify_realtime(
                        db,
                        subscription.user_id,
                        "تم إلغاء اشتراكك",
                        "رجعت لحدود الخطة المجانية.",
                        "billing",
                    )


@router.post("/webhook/stripe", include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    provider = get_payment_provider()
    try:
        event = provider.verify_webhook(payload, dict(request.headers))
    except Exception as exc:
        logger.warning("توقيع Stripe webhook غير صالح: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="توقيع غير صالح")

    await _apply_webhook_event(event, "stripe", db)
    return {"received": True}


@router.post("/webhook/paypal", include_in_schema=False)
async def paypal_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    provider = get_payment_provider()
    if not isinstance(provider, PayPalProvider):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PayPal غير مفعّل")

    try:
        event = await provider.verify_webhook_async(payload, dict(request.headers))
    except Exception as exc:
        logger.warning("توقيع PayPal webhook غير صالح: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="توقيع غير صالح")

    await _apply_webhook_event(event, "paypal", db)
    return {"received": True}
