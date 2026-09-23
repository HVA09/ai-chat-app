from app.tasks import celery_app


def test_celery_app_has_production_scheduled_task():
    assert celery_app is not None
    schedule = celery_app.conf.beat_schedule
    assert "run-due-scheduled-tasks" in schedule
    entry = schedule["run-due-scheduled-tasks"]
    assert entry["task"] == "run_due_scheduled_tasks"
    assert entry["schedule"] == 60.0
