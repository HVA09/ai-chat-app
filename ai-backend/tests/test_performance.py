"""
اختبارات المرحلة الحادية عشرة: تحقق من أن caching وqueue_email يشتغلون بأمان
حتى بدون Redis/Celery متاحين (fallback بدون كسر التطبيق)
"""
from app.cache import cache_delete, cache_get, cache_set
from app.tasks import queue_email


def test_cache_get_returns_none_without_redis():
    # في هذا المشروع كما هو (بدون تثبيت مكتبة redis)، لازم يرجع None دائمًا بأمان
    assert cache_get("any-key") is None


def test_cache_set_and_delete_do_not_raise_without_redis():
    cache_set("any-key", {"a": 1}, 60)
    cache_delete("any-key")  # المهم إنها ما ترمي استثناء


def test_queue_email_falls_back_to_sync_send(monkeypatch):
    sent = {}

    def fake_send_email(to, subject, body):
        sent["to"] = to
        sent["subject"] = subject
        sent["body"] = body

    monkeypatch.setattr("app.tasks.send_email", fake_send_email)
    queue_email("test@example.com", "موضوع", "محتوى")

    assert sent["to"] == "test@example.com"
    assert sent["subject"] == "موضوع"


def test_billing_plans_endpoint_still_works_with_caching_layer(client):
    # يتأكد إن إضافة caching ما كسرت البيانات نفسها (بدون Redis، الكاش يرجع None دائمًا)
    response = client.get("/billing/plans")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_health_check_reports_database_status(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_health_includes_environment(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "environment" in body
    assert "app" in body
    assert "X-Request-ID" in response.headers
