import ssl

from types import SimpleNamespace

from app import tasks as tasks_module
from app.tasks import celery_app


def test_celery_app_has_production_scheduled_task():
    assert celery_app is not None
    schedule = celery_app.conf.beat_schedule
    assert "run-due-scheduled-tasks" in schedule
    entry = schedule["run-due-scheduled-tasks"]
    assert entry["task"] == "run_due_scheduled_tasks"
    assert entry["schedule"] == 60.0
    assert "recover-webhook-deliveries" not in schedule

    # Storage cleanup dispatch is deliberately opt-in; a default deployment
    # must not acquire a new periodic worker until an operator enables it.
    import os

    if os.getenv("STORAGE_CLEANUP_OUTBOX_ENABLED", "").strip().lower() == "true":
        cleanup_entry = schedule["process-storage-cleanup-outbox"]
        assert cleanup_entry["task"] == "process_storage_cleanup_outbox"
        assert cleanup_entry["schedule"] == 60.0
    else:
        assert "process-storage-cleanup-outbox" not in schedule


def test_celery_redis_tls_is_required_only_for_rediss_urls():
    assert celery_app is not None

    verified_tls = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
    assert tasks_module._redis_ssl_options("rediss://cache.example.com:6379/1") == verified_tls
    assert tasks_module._redis_ssl_options("rediss://cache.example.com/0") == verified_tls
    assert tasks_module._redis_ssl_options("redis://localhost:6379/1") is None
    assert tasks_module._redis_ssl_options("redis://127.0.0.1:6379/0") is None

def test_scheduled_task_releases_db_before_provider_wait(monkeypatch):
    events = []
    db = object()

    monkeypatch.setattr(
        tasks_module,
        "commit_and_release_connection",
        lambda session: events.append(("release", session)),
    )

    async def fake_reply(prompt, history, model):
        events.append(("provider", prompt, history, model))
        return SimpleNamespace(text="scheduled reply")

    monkeypatch.setattr(tasks_module, "get_ai_reply", fake_reply)

    reply = tasks_module._scheduled_task_ai_reply(
        db,
        "scheduled prompt",
        "test-model",
    )

    assert reply.text == "scheduled reply"
    assert events == [
        ("release", db),
        ("provider", "scheduled prompt", [], "test-model"),
    ]

def test_celery_cli_application_target_resolves():
    from celery.app.utils import find_app

    assert find_app("app.tasks:celery_app") is celery_app
