"""
إعداد تسجيل الأحداث (Logging) للتطبيق
"""
import logging
import sys

from app.config import settings


def configure_logging() -> None:
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
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
