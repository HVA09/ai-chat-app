"""
اتصال قاعدة البيانات عبر SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# The API, embedded Celery worker, and Celery beat run in separate processes;
# each process creates its own engine. Keep each pool bounded for external session
# poolers with per-user client limits.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT_SECONDS,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency تعطي جلسة DB لكل طلب، وتغلقها تلقائيًا بعد الانتهاء."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
