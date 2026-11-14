"""Regression tests for releasing DB pool slots during remaining external waits."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from starlette.requests import Request

from app.auth import routes as auth_routes
from app.database import Base
from app.models.oauth_connection import OAuthConnection
from app.models.plan import Plan
from app.models.project_file import ProjectFile
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.routers import billing as billing_router
from app.routers import projects as projects_router
from app.schemas.project_preview import PreviewBuildResponse
from app.services import oauth_service


def _pool_database(tmp_path, name, tables):
    engine = create_engine(
        f"sqlite:///{tmp_path / (name + '.sqlite')}",
        poolclass=QueuePool,
        pool_size=1,
        max_overflow=0,
        pool_timeout=1,
    )
    Base.metadata.create_all(bind=engine, tables=tables)
    sessions = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=True,
    )
    return engine, sessions


def _assert_pool_slot_available(engine, sessions):
    assert engine.pool.checkedout() == 0
    with sessions() as contender:
        assert contender.execute(text("SELECT 42")).scalar_one() == 42
    assert engine.pool.checkedout() == 0


def _seed_billing_rows(sessions, suffix):
    with sessions() as db:
        user = User(
            email=f"pool-billing-{suffix}@example.test",
            hashed_password="test-only-password-hash",
        )
        plan = Plan(
            name=f"Pool plan {suffix}",
            price_cents=1900,
            currency="usd",
            interval="month",
            daily_ai_request_limit=100,
            allowed_models=["*"],
            is_active=True,
        )
        db.add_all([user, plan])
        db.flush()
        subscription = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            provider="stripe",
            provider_subscription_id=f"sub-{suffix}",
            status=SubscriptionStatus.active,
        )
        db.add(subscription)
        db.commit()
        return user.id, subscription.id


def _patch_billing_notifications(monkeypatch):
    monkeypatch.setattr(billing_router, "log_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        billing_router,
        "send_subscription_canceled_email",
        lambda *_args, **_kwargs: None,
    )

    async def no_realtime(*_args, **_kwargs):
        return None

    monkeypatch.setattr(billing_router, "notify_realtime", no_realtime)


def test_cancel_subscription_releases_pool_before_provider_wait(
    tmp_path, monkeypatch
):
    engine, sessions = _pool_database(
        tmp_path,
        "billing-cancel",
        [User.__table__, Plan.__table__, Subscription.__table__],
    )
    user_id, subscription_id = _seed_billing_rows(sessions, "cancel")
    _patch_billing_notifications(monkeypatch)

    async def cancel_provider_subscription(provider_subscription_id):
        assert provider_subscription_id == "sub-cancel"
        _assert_pool_slot_available(engine, sessions)

    monkeypatch.setattr(
        billing_router,
        "get_payment_provider",
        lambda: SimpleNamespace(
            cancel_subscription=cancel_provider_subscription
        ),
    )

    db = sessions()
    try:
        current_user = db.get(User, user_id)
        assert current_user is not None
        response = asyncio.run(billing_router.cancel_subscription(current_user, db))
        assert response == {"detail": "تم إلغاء الاشتراك"}

        subscription = db.get(Subscription, subscription_id)
        assert subscription is not None
        assert subscription.status == SubscriptionStatus.canceled
    finally:
        db.close()
        engine.dispose()


def test_cancel_subscription_does_not_overwrite_a_replaced_provider_subscription(
    tmp_path, monkeypatch
):
    engine, sessions = _pool_database(
        tmp_path,
        "billing-cancel-race",
        [User.__table__, Plan.__table__, Subscription.__table__],
    )
    user_id, subscription_id = _seed_billing_rows(sessions, "race")
    _patch_billing_notifications(monkeypatch)

    async def replace_subscription_during_provider_wait(provider_subscription_id):
        assert provider_subscription_id == "sub-race"
        _assert_pool_slot_available(engine, sessions)
        with sessions() as concurrent:
            current = concurrent.get(Subscription, subscription_id)
            assert current is not None
            current.provider_subscription_id = "sub-race-replacement"
            current.status = SubscriptionStatus.active
            concurrent.commit()

    monkeypatch.setattr(
        billing_router,
        "get_payment_provider",
        lambda: SimpleNamespace(
            cancel_subscription=replace_subscription_during_provider_wait
        ),
    )

    db = sessions()
    try:
        current_user = db.get(User, user_id)
        assert current_user is not None
        with pytest.raises(HTTPException) as error:
            asyncio.run(billing_router.cancel_subscription(current_user, db))
        assert error.value.status_code == 409

        current = db.get(Subscription, subscription_id)
        assert current is not None
        assert current.provider_subscription_id == "sub-race-replacement"
        assert current.status == SubscriptionStatus.active
    finally:
        db.close()
        engine.dispose()


def test_billing_webhook_releases_pool_before_sending_activation_email(
    tmp_path, monkeypatch
):
    engine, sessions = _pool_database(
        tmp_path,
        "billing-webhook",
        [User.__table__, Plan.__table__, Subscription.__table__],
    )
    user_id, _ = _seed_billing_rows(sessions, "webhook")

    def send_activation_email(email, plan_name):
        assert email == "pool-billing-webhook@example.test"
        assert plan_name == "Pool plan webhook"
        _assert_pool_slot_available(engine, sessions)

    monkeypatch.setattr(
        billing_router,
        "send_subscription_activated_email",
        send_activation_email,
    )
    monkeypatch.setattr(billing_router, "log_event", lambda *_args, **_kwargs: None)

    async def no_realtime(*_args, **_kwargs):
        return None

    monkeypatch.setattr(billing_router, "notify_realtime", no_realtime)

    event = SimpleNamespace(
        event_type="checkout_completed",
        client_reference_id=str(user_id),
        plan_id="1",
        provider_subscription_id="sub-webhook-activation",
        provider_customer_id="cus-webhook-activation",
    )

    db = sessions()
    try:
        asyncio.run(billing_router._apply_webhook_event(event, "stripe", db))
        subscription = (
            db.query(Subscription)
            .filter(Subscription.user_id == user_id)
            .one()
        )
        assert subscription.provider_subscription_id == "sub-webhook-activation"
        assert subscription.status == SubscriptionStatus.active
    finally:
        db.close()
        engine.dispose()


class _FakeOAuthResponse:
    status_code = 200

    def json(self):
        return {
            "access_token": "stale-provider-access",
            "refresh_token": "stale-provider-refresh",
            "expires_in": 3600,
            "scope": "openid email",
        }


def test_oauth_refresh_releases_pool_and_does_not_overwrite_a_newer_refresh(
    tmp_path, monkeypatch
):
    engine, sessions = _pool_database(
        tmp_path,
        "oauth-refresh",
        [User.__table__, OAuthConnection.__table__],
    )
    monkeypatch.setattr(oauth_service.settings, "OAUTH_GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setattr(oauth_service.settings, "OAUTH_GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(oauth_service.settings, "TOTP_ENCRYPTION_KEY", "")
    monkeypatch.setattr(oauth_service.settings, "JWT_SECRET_KEY", "pool-release-test-secret")

    with sessions() as seed:
        user = User(
            email="pool-oauth@example.test",
            hashed_password="test-only-password-hash",
        )
        seed.add(user)
        seed.flush()
        connection = OAuthConnection(
            user_id=user.id,
            provider="google",
            subject="pool-oauth-subject",
            access_token_encrypted=oauth_service.encrypt_oauth_secret("old-access"),
            refresh_token_encrypted=oauth_service.encrypt_oauth_secret("old-refresh"),
            token_type="Bearer",
            scopes=["openid"],
        )
        seed.add(connection)
        seed.commit()
        connection_id = connection.id

    class ConcurrentRefreshClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, *_args, **_kwargs):
            _assert_pool_slot_available(engine, sessions)
            # A second refresh wins while this provider response is in flight.
            with sessions() as concurrent:
                row = concurrent.get(OAuthConnection, connection_id)
                assert row is not None
                row.access_token_encrypted = oauth_service.encrypt_oauth_secret(
                    "winner-access"
                )
                row.refresh_token_encrypted = oauth_service.encrypt_oauth_secret(
                    "winner-refresh"
                )
                concurrent.commit()
            return _FakeOAuthResponse()

    monkeypatch.setattr(
        oauth_service.httpx,
        "AsyncClient",
        lambda *_args, **_kwargs: ConcurrentRefreshClient(),
    )

    db = sessions()
    try:
        connection = db.get(OAuthConnection, connection_id)
        assert connection is not None
        refreshed = asyncio.run(oauth_service.refresh_oauth_connection(connection, db))
        assert refreshed.id == connection_id
        assert oauth_service.decrypt_oauth_secret(
            refreshed.access_token_encrypted
        ) == "winner-access"
        assert oauth_service.decrypt_oauth_secret(
            refreshed.refresh_token_encrypted
        ) == "winner-refresh"
    finally:
        db.close()
        engine.dispose()


def test_project_preview_releases_pool_before_external_builder_wait(
    tmp_path, monkeypatch
):
    engine, sessions = _pool_database(
        tmp_path,
        "project-preview",
        [ProjectFile.__table__],
    )
    with sessions() as seed:
        seed.add(
            ProjectFile(
                project_id=987,
                path="package.json",
                content='{"scripts":{"build":"vite build"}}',
            )
        )
        seed.commit()

    access_checks = []

    def get_accessible_project(*_args, **_kwargs):
        access_checks.append(987)
        return SimpleNamespace(id=987)

    monkeypatch.setattr(
        projects_router,
        "_get_project",
        get_accessible_project,
    )
    monkeypatch.setattr(
        projects_router,
        "validate_project",
        lambda *_args, **_kwargs: SimpleNamespace(errors=0, project_kind="javascript"),
    )

    async def fake_builder(project_id, files):
        assert project_id == 987
        assert any(item.path == "package.json" for item in files)
        _assert_pool_slot_available(engine, sessions)
        return PreviewBuildResponse(
            entrypoint="dist/index.html",
            artifact_base64="ZmFrZQ==",
            artifact_size_bytes=4,
        )

    published = SimpleNamespace(
        artifact_id="preview-artifact",
        token="preview-token",
        expires_at=4_102_444_800,
        entrypoint="dist/index.html",
        file_paths=("dist/index.html",),
        size_bytes=4,
    )
    monkeypatch.setattr(projects_router, "build_javascript_preview", fake_builder)
    def publish_after_builder(*_args, **_kwargs):
        _assert_pool_slot_available(engine, sessions)
        return published

    monkeypatch.setattr(
        projects_router,
        "publish_preview_artifact",
        publish_after_builder,
    )
    monkeypatch.setattr(
        projects_router,
        "register_preview_artifact",
        lambda *_args, **_kwargs: None,
    )

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": "/projects/987/preview-build",
        "raw_path": b"/projects/987/preview-build",
        "query_string": b"",
        "headers": [],
        "server": ("example.test", 443),
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)

    db = sessions()
    try:
        response = asyncio.run(
            projects_router.build_project_preview(
                987,
                request,
                SimpleNamespace(id=7),
                db,
            )
        )
        assert response.preview_url.startswith(
            "https://example.test/projects/987/preview-artifacts/"
        )
        assert response.preview_expires_at == published.expires_at
        assert access_checks == [987, 987]
    finally:
        db.close()
        engine.dispose()

def test_email_verification_request_releases_pool_before_redis_and_smtp(
    tmp_path, monkeypatch
):
    engine, sessions = _pool_database(
        tmp_path,
        "email-verification-request",
        [User.__table__],
    )
    with sessions() as seed:
        user = User(
            email="pool-verify@example.test",
            hashed_password="test-only-password-hash",
        )
        seed.add(user)
        seed.commit()
        user_id = user.id

    monkeypatch.setattr(
        auth_routes,
        "create_email_verification_token",
        lambda target_user_id: "verification-token",
    )
    monkeypatch.setattr(
        auth_routes,
        "decode_token",
        lambda _token: {"jti": "verification-jti"},
    )

    def remember_verification(jti, ttl):
        assert jti == "verification-jti"
        assert ttl == 24 * 3600
        _assert_pool_slot_available(engine, sessions)
        return True

    def send_verification(email, token):
        assert email == "pool-verify@example.test"
        assert token == "verification-token"
        _assert_pool_slot_available(engine, sessions)

    monkeypatch.setattr(
        auth_routes,
        "remember_email_verification_token",
        remember_verification,
    )
    monkeypatch.setattr(
        auth_routes,
        "send_verification_email",
        send_verification,
    )

    db = sessions()
    try:
        user = db.get(User, user_id)
        assert user is not None
        response = auth_routes.request_email_verification(user, db)
        assert response == {"detail": "تم إرسال رابط التأكيد"}
    finally:
        db.close()
        engine.dispose()


def test_password_reset_request_releases_pool_before_redis_and_smtp(
    tmp_path, monkeypatch
):
    engine, sessions = _pool_database(
        tmp_path,
        "password-reset-request",
        [User.__table__],
    )
    with sessions() as seed:
        user = User(
            email="pool-reset@example.test",
            hashed_password="test-only-password-hash",
        )
        seed.add(user)
        seed.commit()
        user_id = user.id

    monkeypatch.setattr(
        auth_routes,
        "create_password_reset_token",
        lambda target_user_id: "password-reset-token",
    )
    monkeypatch.setattr(
        auth_routes,
        "decode_token",
        lambda _token: {"jti": "password-reset-jti"},
    )

    def remember_reset(jti, ttl):
        assert jti == "password-reset-jti"
        assert ttl == 3600
        _assert_pool_slot_available(engine, sessions)
        return True

    def send_reset(email, token):
        assert email == "pool-reset@example.test"
        assert token == "password-reset-token"
        _assert_pool_slot_available(engine, sessions)

    monkeypatch.setattr(
        auth_routes,
        "remember_password_reset_token",
        remember_reset,
    )
    monkeypatch.setattr(
        auth_routes,
        "send_password_reset_email",
        send_reset,
    )

    db = sessions()
    try:
        assert db.get(User, user_id) is not None
        response = auth_routes.request_password_reset(
            SimpleNamespace(email="pool-reset@example.test"),
            db,
        )
        assert response == {
            "detail": "إذا كان البريد مسجلًا، فسيتم إرسال رابط الاستعادة"
        }
    finally:
        db.close()
        engine.dispose()
