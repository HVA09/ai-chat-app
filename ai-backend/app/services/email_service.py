"""
خدمة إرسال الإيميلات.
لو SMTP_HOST غير مضبوط بـ .env، الإيميل يُطبع في اللوق بدل إرساله فعليًا —
مفيد للتطوير المحلي: تشوف رابط التحقق/إعادة التعيين بالسجلات وتستخدمه يدويًا.
لتفعيل الإرسال الحقيقي: اضبط SMTP_HOST/PORT/USER/PASSWORD بمتغيرات البيئة الخاصة بك.

الدوال هنا (send_verification_email وأخواتها) ترسل عبر queue_email (خلفية عبر Celery
لو متاح، وإلا مباشرة) — الاستيراد مؤجّل داخل كل دالة لتفادي circular import مع app.tasks
(اللي يستورد send_email من هذا الملف).
"""
import smtplib
from email.message import EmailMessage

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("email")


def send_email(to: str, subject: str, body: str) -> None:
    """الإرسال الفعلي (sync) — تستخدمها queue_email مباشرة أو عبر مهمة Celery"""
    if not settings.SMTP_HOST:
        logger.info(
            "=== [DEV MODE] لم يُرسل إيميل حقيقي — اضبط SMTP_HOST لتفعيل الإرسال ===\n"
            "إلى: %s | الموضوع: %s\n%s\n=========================================",
            to,
            subject,
            body,
        )
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(message)
    logger.info("تم إرسال إيميل إلى %s", to)


def send_verification_email(to: str, token: str) -> None:
    from app.tasks import queue_email

    link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    queue_email(
        to=to,
        subject="تأكيد بريدك الإلكتروني",
        body=f"اضغط الرابط لتأكيد بريدك الإلكتروني (صالح 24 ساعة):\n{link}",
    )


def send_password_reset_email(to: str, token: str) -> None:
    from app.tasks import queue_email

    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    queue_email(
        to=to,
        subject="إعادة تعيين كلمة المرور",
        body=f"اضغط الرابط لإعادة تعيين كلمة المرور (صالح ساعة واحدة):\n"
        f"{link}\n\nلو ما طلبت هذا، تجاهل الرسالة.",
    )


def send_welcome_email(to: str) -> None:
    from app.tasks import queue_email

    queue_email(
        to=to,
        subject="أهلًا بك",
        body="تم إنشاء حسابك بنجاح. نتمنى لك تجربة جيدة معنا!",
    )


def send_subscription_activated_email(to: str, plan_name: str) -> None:
    from app.tasks import queue_email

    queue_email(
        to=to,
        subject="تم تفعيل اشتراكك",
        body=f"تم تفعيل اشتراكك بخطة {plan_name} بنجاح. شكرًا لثقتك.",
    )


def send_subscription_canceled_email(to: str) -> None:
    from app.tasks import queue_email

    queue_email(
        to=to,
        subject="تم إلغاء اشتراكك",
        body="تم إلغاء اشتراكك. راح ترجع لحدود الخطة المجانية. تقدر تشترك مرة ثانية بأي وقت.",
    )
