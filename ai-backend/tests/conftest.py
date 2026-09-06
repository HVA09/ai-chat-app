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
    # create_all لا يشغّل بيانات Alembic — نزرع الخطط الافتراضية للاختبارات
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
    """
    كل اختبار يشتغل داخل transaction خارجي + SAVEPOINT داخلي، ويُلغى الاثنان (rollback)
    بعد انتهائه — عزل كامل بين الاختبارات.

    ملاحظة مهمة: session.commit() عادي على session مربوطة بـ connection عندها transaction
    خارجي شغّال بيسكّر هداك الـ transaction فعليًا على قاعدة البيانات (ما فيه "nested
    transactions" حقيقية بدون SAVEPOINT صريح). وبما إن كود التطبيق ينادي db.commit() مباشرة
    بكل مسار تقريبًا (تسجيل، دخول، شات...)، بدون SAVEPOINT هون كان الـ rollback بالنهاية
    ما يلغي شي فعليًا، وبيانات كل اختبار كانت تتراكم بقاعدة الاختبار لباقي التشغيلة
    (وتكسر اختبارات تعتمد على عدّ دقيق متل total_users == 1). هذا هو النمط الموثّق رسميًا
    بتوثيق SQLAlchemy لـ"Joining a Session into an External Transaction".
    """
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # SAVEPOINT داخلي — أي db.commit() من كود التطبيق بيسكّر هاد الـ SAVEPOINT بس، مش
    # الـ transaction الخارجي، فيضل الـ rollback بالنهاية قادر يلغي كل شي
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, transaction):
        # لما SAVEPOINT الحالي يسكّر (بعد commit من كود التطبيق)، افتح وحدة جديدة فورًا
        if transaction.nested and not transaction._parent.nested:
            sess.begin_nested()

    yield session

    event.remove(session, "after_transaction_end", _restart_savepoint)
    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
