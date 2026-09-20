"""مشاركة المساعدين المخصصين داخل مساحة العمل."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.assistant import Assistant
from app.models.assistant_workspace_share import AssistantWorkspaceShare
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.assistant_workspace_shares import (
    AssistantWorkspaceShareOut,
    WorkspaceSharedAssistantOut,
)

router = APIRouter(tags=["Assistant Workspace Sharing"])


def _get_membership(
    workspace_id: int, current_user: User, db: Session
) -> WorkspaceMember:
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


def _get_owned_assistant(
    assistant_id: int, current_user: User, db: Session
) -> Assistant:
    assistant = (
        db.query(Assistant)
        .filter(
            Assistant.id == assistant_id,
            Assistant.user_id == current_user.id,
        )
        .first()
    )
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المساعد غير موجود",
        )
    return assistant


@router.get(
    "/workspaces/{workspace_id}/shared-assistants",
    response_model=list[WorkspaceSharedAssistantOut],
)
def list_workspace_shared_assistants(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_membership(workspace_id, current_user, db)
    rows = (
        db.query(
            AssistantWorkspaceShare,
            Assistant,
            User,
        )
        .join(Assistant, Assistant.id == AssistantWorkspaceShare.assistant_id)
        .join(User, User.id == Assistant.user_id)
        .filter(
            AssistantWorkspaceShare.workspace_id == workspace_id,
        )
        .order_by(AssistantWorkspaceShare.created_at.desc())
        .limit(100)
        .all()
    )
    shared_by_ids = {share.shared_by_user_id for share, _, _ in rows}
    shared_by_emails = {}
    if shared_by_ids:
        shared_by_emails = dict(
            db.query(User.id, User.email)
            .filter(User.id.in_(shared_by_ids))
            .all()
        )

    return [
        WorkspaceSharedAssistantOut(
            id=assistant.id,
            name=assistant.name,
            description=assistant.description,
            owner_user_id=assistant.user_id,
            owner_email=owner.email,
            workspace_id=workspace_id,
            shared_at=share.created_at,
            is_shared=True,
            can_edit=assistant.user_id == current_user.id,
        )
        for share, assistant, owner in rows
    ]


@router.post(
    "/assistants/{assistant_id}/workspace-share/{workspace_id}",
    response_model=AssistantWorkspaceShareOut,
    status_code=status.HTTP_201_CREATED,
)
def share_assistant_with_workspace(
    assistant_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assistant = _get_owned_assistant(assistant_id, current_user, db)
    _get_membership(workspace_id, current_user, db)

    existing = (
        db.query(AssistantWorkspaceShare)
        .filter(
            AssistantWorkspaceShare.assistant_id == assistant.id,
            AssistantWorkspaceShare.workspace_id == workspace_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="المساعد مشترك بالفعل مع مساحة العمل",
        )

    share = AssistantWorkspaceShare(
        assistant_id=assistant.id,
        workspace_id=workspace_id,
        shared_by_user_id=current_user.id,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return AssistantWorkspaceShareOut(
        id=share.id,
        assistant_id=share.assistant_id,
        workspace_id=share.workspace_id,
        shared_by_user_id=share.shared_by_user_id,
        shared_by_email=current_user.email,
        created_at=share.created_at,
    )


@router.delete(
    "/assistants/{assistant_id}/workspace-share/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unshare_assistant_from_workspace(
    assistant_id: int,
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assistant = _get_owned_assistant(assistant_id, current_user, db)
    _get_membership(workspace_id, current_user, db)
    share = (
        db.query(AssistantWorkspaceShare)
        .filter(
            AssistantWorkspaceShare.assistant_id == assistant.id,
            AssistantWorkspaceShare.workspace_id == workspace_id,
        )
        .first()
    )
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مشاركة المساعد غير موجودة",
        )
    db.delete(share)
    db.commit()
