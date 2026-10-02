"""Persistent multi-step Agent workflow API."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.agent_workflow import AgentWorkflow, AgentWorkflowStep
from app.models.conversation import Conversation, Message, MessageRole
from app.models.project import WorkspaceProject
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.agent_workflows import (
    AgentWorkflowCancelOut,
    AgentWorkflowCreate,
    AgentWorkflowOut,
    AgentWorkflowResumeOut,
)
from app.services.agent_workflow import execute_agent_workflow
from app.services.project_access import can_edit_project
from app.tasks import celery_app


router = APIRouter(prefix="/agent-workflows", tags=["Agent Workflows"])


def _get_membership(workspace_id: int, current_user: User, db: Session) -> WorkspaceMember:
    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مساحة العمل غير موجودة",
        )
    return membership


def _get_owned_workflow(workflow_id: int, current_user: User, db: Session) -> AgentWorkflow:
    workflow = (
        db.query(AgentWorkflow)
        .filter(
            AgentWorkflow.id == workflow_id,
            AgentWorkflow.user_id == current_user.id,
        )
        .first()
    )
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الـworkflow غير موجود",
        )
    return workflow


def _queue(workflow_id: int, db: Session, workflow: AgentWorkflow) -> None:
    if celery_app is None:
        execute_agent_workflow(workflow_id, db=db)
        return

    try:
        celery_result = celery_app.send_task("execute_agent_workflow", args=[workflow_id])
        workflow.error = None
        workflow.status = "queued"
        db.commit()
        workflow.checkpoint = {
            **(workflow.checkpoint or {}),
            "queued_task_id": celery_result.id,
        }
        db.commit()
    except Exception as exc:
        workflow.status = "failed"
        workflow.error = "تعذر جدولة workflow حاليًا."
        workflow.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="تعذر جدولة workflow حاليًا",
        ) from exc


@router.post("", response_model=AgentWorkflowOut, status_code=status.HTTP_202_ACCEPTED)
def create_agent_workflow(
    payload: AgentWorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_membership(payload.workspace_id, current_user, db)
    workspace = db.get(Workspace, payload.workspace_id)
    project = db.get(WorkspaceProject, payload.project_id)
    if workspace is None or project is None or project.workspace_id != payload.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المشروع غير موجود ضمن مساحة العمل.",
        )
    if not can_edit_project(project, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المشروع غير موجود ضمن مساحة العمل.",
        )

    conversation = Conversation(
        user_id=current_user.id,
        workspace_id=payload.workspace_id,
        project_id=project.id,
        title=payload.name[:120],
        ai_model=workspace.default_ai_model,
    )
    db.add(conversation)
    db.flush()

    workflow = AgentWorkflow(
        user_id=current_user.id,
        workspace_id=payload.workspace_id,
        project_id=project.id,
        conversation_id=conversation.id,
        name=payload.name,
        status="queued",
        checkpoint={
            "version": 1,
            "current_step_position": 1,
            "last_completed_step_position": 0,
            "completed_steps": [],
        },
    )
    db.add(workflow)
    db.flush()

    workflow_message = "\n".join(
        f"{index}. {step.name}: {step.instruction}"
        for index, step in enumerate(payload.steps, start=1)
    )
    db.add(
        Message(
            conversation_id=conversation.id,
            role=MessageRole.user,
            content=f"[AGENT WORKFLOW]\n{payload.name}\n\n{workflow_message}",
        )
    )

    for position, step_payload in enumerate(payload.steps, start=1):
        db.add(
            AgentWorkflowStep(
                workflow_id=workflow.id,
                position=position,
                name=step_payload.name,
                instruction=step_payload.instruction,
            )
        )
    db.commit()
    db.refresh(workflow)

    _queue(workflow.id, db, workflow)
    db.refresh(workflow)
    return workflow


@router.get("", response_model=list[AgentWorkflowOut])
def list_agent_workflows(
    workspace_id: int | None = None,
    project_id: int | None = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(AgentWorkflow).filter(AgentWorkflow.user_id == current_user.id)
    if workspace_id is not None:
        _get_membership(workspace_id, current_user, db)
        query = query.filter(AgentWorkflow.workspace_id == workspace_id)
    if project_id is not None:
        project = db.get(WorkspaceProject, project_id)
        if project is None or not can_edit_project(project, current_user, db):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="المشروع غير موجود ضمن مساحة العمل.",
            )
        query = query.filter(AgentWorkflow.project_id == project_id)
    limit = min(max(limit, 1), 50)
    return query.order_by(AgentWorkflow.created_at.desc(), AgentWorkflow.id.desc()).limit(limit).all()


@router.get("/{workflow_id}", response_model=AgentWorkflowOut)
def get_agent_workflow(
    workflow_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_workflow(workflow_id, current_user, db)


@router.post("/{workflow_id}/cancel", response_model=AgentWorkflowCancelOut)
def cancel_agent_workflow(
    workflow_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workflow = _get_owned_workflow(workflow_id, current_user, db)
    if workflow.status in {"succeeded", "failed", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="لا يمكن إلغاء workflow انتهى.",
        )
    workflow.cancel_requested = True
    if workflow.status == "queued":
        workflow.status = "cancelled"
        workflow.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.post("/{workflow_id}/resume", response_model=AgentWorkflowResumeOut)
def resume_agent_workflow(
    workflow_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workflow = _get_owned_workflow(workflow_id, current_user, db)
    if workflow.status not in {"failed", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="يمكن استئناف workflow متوقف فقط.",
        )

    if workflow.status == "failed":
        current_step = next(
            (
                step for step in workflow.steps
                if step.position == workflow.current_step_position
                and step.status == "failed"
            ),
            None,
        )
        if current_step is not None:
            current_step.status = "queued"
            current_step.error = None

    workflow.cancel_requested = False
    workflow.status = "queued"
    workflow.error = None
    workflow.finished_at = None
    db.commit()

    _queue(workflow.id, db, workflow)
    db.refresh(workflow)
    return workflow
