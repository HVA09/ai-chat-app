"""
إعداد تسجيل الأحداث (Logging) للتطبيق
"""
import logging
import sys
from contextvars import ContextVar

from app.config import settings

_request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(request_id: str):
    """Set the request ID for the current async execution context."""
    return _request_id_context.set(request_id)


def reset_request_id(token) -> None:
    """Restore the previous request ID after a request finishes."""
    _request_id_context.reset(token)


def get_request_id() -> str:
    """Return the request ID for the current async execution context."""
    return _request_id_context.get()


class RequestIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def configure_logging() -> None:
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdLogFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | "
            "[request_id=%(request_id)s] | %(message)s"
        )
    )

    root_logger = logging.getLogger("app")
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.propagate = False

    # تقليل ضجيج مكتبات خارجية (كل استعلام SQL كان يطبع سطر لو ما سوينا هذا)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"app.{name}")
