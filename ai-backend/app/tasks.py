"""
مهام خلفية (Celery) — إرسال الإيميل بالخصوص، عشان ما يبطّئ الرد على الطلب بانتظار SMTP.

لو مكتبة celery غير مثبّتة، أو Redis/الـ worker مو شغّالين، queue_email() ترجع
تلقائيًا للإرسال المباشر (sync) بدل ما تفشل الطلب كامل — التطبيق يشتغل حتى بدون
Celery مضبوط، بس بدون فايدة "الخلفية" وقتها.
"""
from app.logging_config import get_logger
from app.services.email_service import send_email

logger = get_logger("tasks")

try:
    from celery import Celery

    from app.config import settings

    celery_app = Celery(
        "ai_backend",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )

    @celery_app.task(name="send_email_task")
    def send_email_task(to: str, subject: str, body: str) -> None:
        send_email(to, subject, body)

    _CELERY_AVAILABLE = True
except ImportError:
    celery_app = None
    send_email_task = None
    _CELERY_AVAILABLE = False
    logger.info("مكتبة celery غير مثبّتة — الإيميلات تُرسل مباشرة (sync) بدون طابور خلفي")


def queue_email(to: str, subject: str, body: str) -> None:
    """يحاول جدولة الإيميل عبر Celery؛ لو مو متاح أو فشل الاتصال بـ Redis، يرسله مباشرة"""
    if _CELERY_AVAILABLE:
        try:
            send_email_task.delay(to, subject, body)
            return
        except Exception:
            logger.warning("تعذر إرسال المهمة لـ Celery/Redis — إرسال مباشر بدلها")
    send_email(to, subject, body)
