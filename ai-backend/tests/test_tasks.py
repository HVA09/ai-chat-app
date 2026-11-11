import ssl

from app.tasks import celery_app


def test_celery_app_has_production_scheduled_task():
    assert celery_app is not None
    schedule = celery_app.conf.beat_schedule
    assert "run-due-scheduled-tasks" in schedule
    entry = schedule["run-due-scheduled-tasks"]
    assert entry["task"] == "run_due_scheduled_tasks"
    assert entry["schedule"] == 60.0


def test_celery_redis_connections_require_verified_tls():
    assert celery_app is not None
    assert celery_app.conf.broker_use_ssl == {"ssl_cert_reqs": ssl.CERT_REQUIRED}
    assert celery_app.conf.redis_backend_use_ssl == {"ssl_cert_reqs": ssl.CERT_REQUIRED}
