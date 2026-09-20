"""مسارات مساحة العمل الحالية للمستخدم."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.usage_log import UsageLog
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.audit import log_event
from app.schemas.workspace_audit import WorkspaceAuditLogOut
from app.schemas.workspaces import (
    WorkspaceCreate,
    WorkspaceDefaultModelUpdate,
    WorkspaceOut,
    WorkspaceRename,
)
from app.schemas.workspace_usage import WorkspaceUsageMemberOut, WorkspaceUsageOut
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


def _get_membership(
    workspace_id: int, current_user: User, db: Session
) -> WorkspaceMember:
    membership = (
        db.query(WorkspaceMember)
        .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
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


def _ensure_unique_owned_name(
    name: str, owner_id: int, db: Session, exclude_id: int | None = None
) -> None:
    query = db.query(Workspace).filter(
        Workspace.owner_id == owner_id,
        func.lower(Workspace.name) == func.lower(name.strip()),
    )
    if exclude_id is not None:
        query = query.filter(Workspace.id != exclude_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="لديك مساحة عمل بهذا الاسم",
        )


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .filter(WorkspaceMember.user_id == current_user.id)
        .order_by(Workspace.created_at.asc(), Workspace.id.asc())
        .all()
    )
    return [
        WorkspaceOut(
            id=workspace.id,
            name=workspace.name,
            role=role,
            default_ai_model=workspace.default_ai_model,
            created_at=workspace.created_at,
        )
        for workspace, role in rows
    ]


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_unique_owned_name(payload.name, current_user.id, db)
    workspace = Workspace(owner_id=current_user.id, name=payload.name)
    db.add(workspace)
    db.flush()
    db.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=current_user.id,
            role=WorkspaceRole.owner,
        )
    )
    db.commit()
    db.refresh(workspace)
    log_event(
        db,
        "workspace_created",
        f"تم إنشاء مساحة العمل {workspace.name}",
        current_user.id,
        workspace.id,
    )
    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        role=WorkspaceRole.owner,
        default_ai_model=workspace.default_ai_model,
        created_at=workspace.created_at,
    )


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
def rename_workspace(
    workspace_id: int,
    payload: WorkspaceRename,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = _get_membership(workspace_id, current_user, db)
    if membership.role not in {WorkspaceRole.owner, WorkspaceRole.admin}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذه العملية تتطلب صلاحية مدير مساحة العمل",
        )

    workspace = membership.workspace
    _ensure_unique_owned_name(
        payload.name,
        workspace.owner_id,
        db,
        exclude_id=workspace.id,
    )
    old_name = workspace.name
    workspace.name = payload.name
    db.commit()
    db.refresh(workspace)
    log_event(
        db,
        "workspace_renamed",
        f"تم تغيير اسم مساحة العمل من {old_name} إلى {workspace.name}",
        current_user.id,
        workspace.id,
    )
    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        role=membership.role,
        default_ai_model=workspace.default_ai_model,
        created_at=workspace.created_at,
    )


@router.patch("/{workspace_id}/model", response_model=WorkspaceOut)
def update_workspace_default_model(
    workspace_id: int,
    payload: WorkspaceDefaultModelUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = _get_membership(workspace_id, current_user, db)
    if membership.role not in {WorkspaceRole.owner, WorkspaceRole.admin}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذه العملية تتطلب صلاحية مدير مساحة العمل",
        )

    if payload.model is not None and payload.model not in settings.AI_ALLOWED_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="نموذج الذكاء الاصطناعي غير متاح في الإعدادات الحالية",
        )

    workspace = membership.workspace
    workspace.default_ai_model = payload.model
    db.commit()
    db.refresh(workspace)

    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        role=membership.role,
        default_ai_model=workspace.default_ai_model,
        created_at=workspace.created_at,
    )


@router.get("/{workspace_id}/usage", response_model=WorkspaceUsageOut)
def get_workspace_usage(
    workspace_id: int,
    window_hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = _get_membership(workspace_id, current_user, db)
    if membership.role not in {WorkspaceRole.owner, WorkspaceRole.admin}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذه العملية تتطلب صلاحية مدير مساحة العمل",
        )

    window_hours = max(1, min(window_hours, 168))
    window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

    base_query = (
        db.query(UsageLog)
        .join(
            WorkspaceMember,
            WorkspaceMember.user_id == UsageLog.user_id,
        )
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            UsageLog.created_at >= window_start,
        )
    )

    totals = base_query.with_entities(
        func.count(UsageLog.id),
        func.coalesce(func.sum(UsageLog.input_tokens), 0),
        func.coalesce(func.sum(UsageLog.output_tokens), 0),
    ).one()

    member_rows = (
        db.query(
            User.id,
            User.email,
            User.full_name,
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.input_tokens), 0),
            func.coalesce(func.sum(UsageLog.output_tokens), 0),
        )
        .join(WorkspaceMember, WorkspaceMember.user_id == User.id)
        .outerjoin(
            UsageLog,
            (UsageLog.user_id == User.id)
            & (UsageLog.created_at >= window_start),
        )
        .filter(WorkspaceMember.workspace_id == workspace_id)
        .group_by(User.id, User.email, User.full_name)
        .order_by(func.count(UsageLog.id).desc(), User.email.asc())
        .all()
    )

    members = [
        WorkspaceUsageMemberOut(
            user_id=user_id,
            email=email,
            full_name=full_name,
            used_requests=int(used_requests or 0),
            input_tokens=int(input_tokens or 0),
            output_tokens=int(output_tokens or 0),
            total_tokens=int(input_tokens or 0) + int(output_tokens or 0),
        )
        for user_id, email, full_name, used_requests, input_tokens, output_tokens in member_rows
    ]

    used_requests = int(totals[0] or 0)
    input_tokens = int(totals[1] or 0)
    output_tokens = int(totals[2] or 0)

    return WorkspaceUsageOut(
        workspace_id=workspace_id,
        window_hours=window_hours,
        window_start=window_start,
        used_requests=used_requests,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        members=members,
    )


@router.get("/{workspace_id}/audit-logs", response_model=list[WorkspaceAuditLogOut])
def list_workspace_audit_logs(
    workspace_id: int,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = _get_membership(workspace_id, current_user, db)
    if membership.role not in {WorkspaceRole.owner, WorkspaceRole.admin}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذه العملية تتطلب صلاحية مدير مساحة العمل",
        )

    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    rows = (
        db.query(AuditLog, User.email)
        .outerjoin(User, AuditLog.user_id == User.id)
        .filter(AuditLog.workspace_id == workspace_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        WorkspaceAuditLogOut(
            id=log.id,
            user_id=log.user_id,
            actor_email=email,
            event_type=log.event_type,
            description=log.description,
            created_at=log.created_at,
        )
        for log, email in rows
    ]
