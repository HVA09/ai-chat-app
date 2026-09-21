"""اختبارات المنطقة الزمنية للمهام المجدولة."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.models.scheduled_task import ScheduledTask, ScheduledTaskType
from app.tasks import _next_occurrence
from app.schemas.scheduled_tasks import ScheduledTaskCreate


def test_next_occurrence_preserves_local_wall_clock_across_dst():
    task = ScheduledTask(
        schedule_type=ScheduledTaskType.daily,
        next_run_at=datetime(2026, 3, 28, 9, 0, tzinfo=timezone.utc),
        timezone_name="Europe/Berlin",
    )
    now = datetime(2026, 3, 28, 10, 0, tzinfo=ZoneInfo("Europe/Berlin"))

    next_run = _next_occurrence(task, now)

    assert next_run == datetime(2026, 3, 29, 8, 0, tzinfo=timezone.utc)
    assert next_run.astimezone(ZoneInfo("Europe/Berlin")).hour == 10


def test_next_occurrence_uses_weekly_local_time():
    task = ScheduledTask(
        schedule_type=ScheduledTaskType.weekly,
        next_run_at=datetime(2026, 7, 1, 16, 0, tzinfo=timezone.utc),
        timezone_name="Africa/Tripoli",
    )
    now = datetime(2026, 7, 2, 20, 0, tzinfo=ZoneInfo("Africa/Tripoli"))

    next_run = _next_occurrence(task, now)

    assert next_run.astimezone(ZoneInfo("Africa/Tripoli")).hour == 18
    assert next_run.weekday() == 2


def test_scheduled_task_create_rejects_invalid_timezone():
    with pytest.raises(ValidationError):
        ScheduledTaskCreate(
            workspace_id=1,
            prompt="اختبار",
            schedule_type="daily",
            next_run_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
            timezone_name="Not/A_Timezone",
        )


def test_scheduled_task_timezone_defaults_to_utc():
    payload = ScheduledTaskCreate(
        workspace_id=1,
        prompt="اختبار",
        schedule_type="once",
        next_run_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )
    assert payload.timezone_name == "UTC"
