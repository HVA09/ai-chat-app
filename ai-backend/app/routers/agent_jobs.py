"""Long-running Agent Platform jobs."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.agent_job import AgentJob
from app.models.conversation import Conversation, Message, MessageRole
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.agent_jobs import AgentJobCancelOut, AgentJobCreate, AgentJobOut
from app.tasks import execute_agent_job, celery_app

router = APIRouter(prefix="/agent-jobs", tags=["Agent Jobs"])


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


def _get_owned_job(job_id: int, current_user: User, db: Session) -> AgentJob:
    job = (
        db.query(AgentJob)
        .filter(
            AgentJob.id == job_id,
            AgentJob.user_id == current_user.id,
        )
        .first()
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مهمة الوكيل غير موجودة",
        )
    return job


@router.post("", response_model=AgentJobOut, status_code=status.HTTP_202_ACCEPTED)
def create_agent_job(
    payload: AgentJobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = payload.normalized_task()
    _get_membership(payload.workspace_id, current_user, db)

    workspace_obj = db.get(Workspace, payload.workspace_id)
    if workspace_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مساحة العمل غير موجودة",
        )
    conversation = Conversation(
        user_id=current_user.id,
        workspace_id=payload.workspace_id,
        title=task[:50] or "Agent Job",
        ai_model=workspace_obj.default_ai_model,
    )
    db.add(conversation)
    db.flush()
    db.add(
        Message(
            conversation_id=conversation.id,
            role=MessageRole.user,
            content=task,
        )
    )

    job = AgentJob(
        user_id=current_user.id,
        workspace_id=payload.workspace_id,
        conversation_id=conversation.id,
        task=task,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if execute_agent_job is None or celery_app is None:
        job.status = "failed"
        job.error = "خدمة المهام الخلفية غير متاحة حاليًا."
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="خدمة المهام الخلفية غير متاحة حاليًا",
        )

    try:
        async_result = execute_agent_job.delay(job.id)
        job.celery_task_id = async_result.id
        db.commit()
        db.refresh(job)
    except Exception as exc:
        job.status = "failed"
        job.error = "تعذر وضع المهمة في طابور التنفيذ."
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="تعذر جدولة مهمة الوكيل حاليًا",
        ) from exc

    return job


@router.get("", response_model=list[AgentJobOut])
def list_agent_jobs(
    workspace_id: int | None = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(AgentJob).filter(AgentJob.user_id == current_user.id)
    if workspace_id is not None:
        _get_membership(workspace_id, current_user, db)
        query = query.filter(AgentJob.workspace_id == workspace_id)
    limit = min(max(limit, 1), 100)
    return query.order_by(AgentJob.created_at.desc(), AgentJob.id.desc()).limit(limit).all()


@router.get("/{job_id}", response_model=AgentJobOut)
def get_agent_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_job(job_id, current_user, db)


@router.post("/{job_id}/cancel", response_model=AgentJobCancelOut)
def cancel_agent_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = _get_owned_job(job_id, current_user, db)

    if job.status in {"succeeded", "failed", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="لا يمكن إلغاء مهمة انتهت.",
        )

    job.cancel_requested = True
    if job.status == "queued":
        job.status = "cancelled"
        job.finished_at = datetime.now(timezone.utc)

    if job.celery_task_id and celery_app is not None:
        try:
            celery_app.control.revoke(job.celery_task_id, terminate=False)
        except Exception:
            # الإلغاء التعاوني عبر قاعدة البيانات يبقى المصدر الأساسي للحالة.
            pass

    db.commit()
    db.refresh(job)
    return job
