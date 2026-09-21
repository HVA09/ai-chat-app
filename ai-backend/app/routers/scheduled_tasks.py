"""مسارات إنشاء وإدارة المهام المجدولة."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.scheduled_task import ScheduledTask, ScheduledTaskType
from app.models.scheduled_task_run import ScheduledTaskRun
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.schemas.scheduled_task_runs import ScheduledTaskRunOut
from app.schemas.scheduled_tasks import (
    ScheduledTaskCreate,
    ScheduledTaskOut,
    ScheduledTaskUpdate,
)

router = APIRouter(prefix="/scheduled-tasks", tags=["Scheduled Tasks"])


def _get_membership(workspace_id: int, current_user: User, db: Session) -> WorkspaceMember:
    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مساحة العمل غير موجودة",
        )
    return membership


def _get_owned_task(task_id: int, current_user: User, db: Session) -> ScheduledTask:
    task = (
        db.query(ScheduledTask)
        .filter(
            ScheduledTask.id == task_id,
            ScheduledTask.user_id == current_user.id,
        )
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المهمة المجدولة غير موجودة",
        )
    return task


def _validate_schedule(
    schedule_type: str,
    next_run_at: datetime,
    weekday: int | None,
) -> None:
    normalized = next_run_at.astimezone(timezone.utc)
    if normalized <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="وقت التنفيذ يجب أن يكون في المستقبل",
        )
    if schedule_type == ScheduledTaskType.weekly.value and weekday is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="يجب تحديد يوم الأسبوع للمهمة الأسبوعية",
        )


@router.get("", response_model=list[ScheduledTaskOut])
def list_scheduled_tasks(
    workspace_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ScheduledTask).filter(ScheduledTask.user_id == current_user.id)
    if workspace_id is not None:
        _get_membership(workspace_id, current_user, db)
        query = query.filter(ScheduledTask.workspace_id == workspace_id)
    return query.order_by(ScheduledTask.is_active.desc(), ScheduledTask.next_run_at.asc()).all()


@router.post("", response_model=ScheduledTaskOut, status_code=status.HTTP_201_CREATED)
def create_scheduled_task(
    payload: ScheduledTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_membership(payload.workspace_id, current_user, db)
    _validate_schedule(payload.schedule_type, payload.next_run_at, payload.weekday)

    task = ScheduledTask(
        user_id=current_user.id,
        workspace_id=payload.workspace_id,
        prompt=payload.prompt,
        schedule_type=ScheduledTaskType(payload.schedule_type),
        next_run_at=payload.next_run_at.astimezone(timezone.utc),
        weekday=payload.weekday,
        is_active=True,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=ScheduledTaskOut)
def update_scheduled_task(
    task_id: int,
    payload: ScheduledTaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(task_id, current_user, db)
    values = payload.model_dump(exclude_unset=True)

    if "next_run_at" in values and values["next_run_at"] is not None:
        values["next_run_at"] = values["next_run_at"].astimezone(timezone.utc)

    schedule_type = values.get("schedule_type", task.schedule_type.value)
    next_run_at = values.get("next_run_at", task.next_run_at)
    weekday = values.get("weekday", task.weekday)
    if schedule_type and next_run_at:
        _validate_schedule(schedule_type, next_run_at, weekday)

    if "prompt" in values:
        task.prompt = values["prompt"]
    if "schedule_type" in values:
        task.schedule_type = ScheduledTaskType(values["schedule_type"])
    if "next_run_at" in values and values["next_run_at"] is not None:
        task.next_run_at = values["next_run_at"]
    if "weekday" in values:
        task.weekday = values["weekday"]
    if "is_active" in values:
        task.is_active = values["is_active"]
        if task.is_active:
            task.last_error = None

    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}/runs", response_model=list[ScheduledTaskRunOut])
def list_scheduled_task_runs(
    task_id: int,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_task(task_id, current_user, db)
    limit = min(max(limit, 1), 100)
    return (
        db.query(ScheduledTaskRun)
        .filter(ScheduledTaskRun.scheduled_task_id == task_id)
        .order_by(ScheduledTaskRun.created_at.desc(), ScheduledTaskRun.id.desc())
        .limit(limit)
        .all()
    )


@router.post("/{task_id}/run", response_model=ScheduledTaskRunOut, status_code=status.HTTP_202_ACCEPTED)
def run_scheduled_task_now(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(task_id, current_user, db)
    run = ScheduledTaskRun(
        scheduled_task_id=task.id,
        user_id=current_user.id,
        workspace_id=task.workspace_id,
        prompt=task.prompt,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        from app.tasks import execute_scheduled_task
        if execute_scheduled_task is not None:
            execute_scheduled_task.delay(task.id, run.id)
            return run
    except Exception:
        # Redis/Celery قد لا يكون متاحًا في التطوير؛ ننفذ مباشرة كـ fallback.
        pass

    from app.tasks import _execute_scheduled_task
    _execute_scheduled_task(task.id, run.id)
    db.refresh(run)
    return run


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheduled_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(task_id, current_user, db)
    db.delete(task)
    db.commit()
