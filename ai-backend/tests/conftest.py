import os
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-ci-only")
os.environ.setdefault("AI_API_KEY", "test-key-not-real")
"""
إعداد fixtures للاختبارات: قاعدة بيانات PostgreSQL منفصلة للاختبار + FastAPI TestClient.
اضبط TEST_DATABASE_URL في البيئة قبل التشغيل (راجع README.md).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ai_backend_test"
)

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    from app.models.plan import Plan
    session = TestingSessionLocal()
    try:
        if session.query(Plan).count() == 0:
            session.add_all(
                [
                    Plan(
                        name="Free",
                        price_cents=0,
                        currency="usd",
                        interval="month",
                        daily_ai_request_limit=20,
                        is_active=True,
                    ),
                    Plan(
                        name="Pro",
                        price_cents=1900,
                        currency="usd",
                        interval="month",
                        daily_ai_request_limit=200,
                        is_active=True,
                    ),
                ]
            )
            session.commit()
    finally:
        session.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, transaction):
        if transaction.nested and not transaction._parent.nested:
            sess.begin_nested()

    yield session

    event.remove(session, "after_transaction_end", _restart_savepoint)
    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def reset_test_security_state(monkeypatch):
    """Keep security middleware deterministic in pytest without weakening production."""
    from app.config import settings as app_settings
    from app.middleware import _hits

    monkeypatch.setattr(app_settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(app_settings, "INITIAL_ADMIN_EMAIL", None)
    _hits.clear()
    yield
    _hits.clear()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
