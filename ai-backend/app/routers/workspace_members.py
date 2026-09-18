"""إدارة أعضاء ودعوات مساحات العمل."""
from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.workspace_invitation import WorkspaceInvitation
from app.notifications import notify
from app.schemas.workspace_members import (
    WorkspaceInvitationAccept,
    WorkspaceInvitationAcceptOut,
    WorkspaceInvitationOut,
    WorkspaceInviteCreate,
    WorkspaceMemberOut,
    WorkspaceRoleUpdate,
)
from app.services.email_service import send_workspace_invitation_email
from app.validators import normalize_email

router = APIRouter(tags=["Workspace Members"])


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
        raise HTTPException(status_code=404, detail="مساحة العمل غير موجودة")
    return membership


def _require_manager(workspace_id: int, current_user: User, db: Session) -> WorkspaceMember:
    membership = _get_membership(workspace_id, current_user, db)
    if membership.role not in {WorkspaceRole.owner, WorkspaceRole.admin}:
        raise HTTPException(status_code=403, detail="هذه العملية تتطلب صلاحية إدارة مساحة العمل")
    return membership


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.get("/workspaces/{workspace_id}/members", response_model=list[WorkspaceMemberOut])
def list_workspace_members(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_membership(workspace_id, current_user, db)
    rows = (
        db.query(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .filter(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.created_at.asc())
        .all()
    )
    return [
        WorkspaceMemberOut(
            id=member.id,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=member.role,
            created_at=member.created_at,
        )
        for member, user in rows
    ]


@router.post(
    "/workspaces/{workspace_id}/invitations",
    response_model=WorkspaceInvitationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace_invitation(
    workspace_id: int,
    payload: WorkspaceInviteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = _require_manager(workspace_id, current_user, db)
    if membership.role == WorkspaceRole.admin and payload.role == WorkspaceRole.admin:
        raise HTTPException(
            status_code=403,
            detail="مدير مساحة العمل لا يمكنه منح صلاحية مدير آخر",
        )
    target = db.query(User).filter(User.email == normalize_email(payload.email)).first()
    if not target:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود. الدعوات الحالية تتطلب حسابًا مسجلًا.")
    if target.id == current_user.id:
        raise HTTPException(status_code=409, detail="لا يمكنك دعوة نفسك")
    if db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == target.id,
    ).first():
        raise HTTPException(status_code=409, detail="المستخدم عضو بالفعل في مساحة العمل")

    now = datetime.now(timezone.utc)
    if db.query(WorkspaceInvitation).filter(
        WorkspaceInvitation.workspace_id == workspace_id,
        WorkspaceInvitation.invited_user_id == target.id,
        WorkspaceInvitation.accepted_at.is_(None),
        WorkspaceInvitation.revoked_at.is_(None),
        WorkspaceInvitation.expires_at > now,
    ).first():
        raise HTTPException(status_code=409, detail="هناك دعوة معلقة لهذا المستخدم")

    token = secrets.token_urlsafe(32)
    invitation = WorkspaceInvitation(
        workspace_id=workspace_id,
        invited_by_user_id=current_user.id,
        invited_user_id=target.id,
        email=target.email,
        role=payload.role,
        token_hash=_hash_token(token),
        expires_at=now + timedelta(days=7),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    send_workspace_invitation_email(
        to=target.email,
        workspace_name=membership.workspace.name,
        inviter_email=current_user.email,
        token=token,
    )
    notify(
        db,
        target.id,
        "دعوة إلى مساحة عمل",
        f"تمت دعوتك للانضمام إلى {membership.workspace.name}.",
        "workspace_invitation",
    )
    return invitation


@router.get("/workspaces/{workspace_id}/invitations", response_model=list[WorkspaceInvitationOut])
def list_workspace_invitations(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_manager(workspace_id, current_user, db)
    now = datetime.now(timezone.utc)
    return (
        db.query(WorkspaceInvitation)
        .filter(
            WorkspaceInvitation.workspace_id == workspace_id,
            WorkspaceInvitation.accepted_at.is_(None),
            WorkspaceInvitation.revoked_at.is_(None),
            WorkspaceInvitation.expires_at > now,
        )
        .order_by(WorkspaceInvitation.created_at.desc())
        .all()
    )


@router.delete("/workspaces/{workspace_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_workspace_invitation(
    workspace_id: int,
    invitation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_manager(workspace_id, current_user, db)
    invitation = db.query(WorkspaceInvitation).filter(
        WorkspaceInvitation.id == invitation_id,
        WorkspaceInvitation.workspace_id == workspace_id,
        WorkspaceInvitation.accepted_at.is_(None),
        WorkspaceInvitation.revoked_at.is_(None),
    ).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="الدعوة غير موجودة")
    invitation.revoked_at = datetime.now(timezone.utc)
    db.commit()


@router.patch("/workspaces/{workspace_id}/members/{member_id}/role", response_model=WorkspaceMemberOut)
def update_workspace_member_role(
    workspace_id: int,
    member_id: int,
    payload: WorkspaceRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = _get_membership(workspace_id, current_user, db)
    if membership.role != WorkspaceRole.owner:
        raise HTTPException(status_code=403, detail="تغيير أدوار الأعضاء للمالك فقط")

    target = (
        db.query(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .filter(WorkspaceMember.id == member_id, WorkspaceMember.workspace_id == workspace_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="العضو غير موجود")
    target_member, target_user = target
    if target_member.role == WorkspaceRole.owner:
        raise HTTPException(status_code=403, detail="لا يمكن تغيير دور مالك مساحة العمل")

    target_member.role = payload.role
    db.commit()
    db.refresh(target_member)
    return WorkspaceMemberOut(
        id=target_member.id,
        user_id=target_user.id,
        email=target_user.email,
        full_name=target_user.full_name,
        role=target_member.role,
        created_at=target_member.created_at,
    )


@router.delete("/workspaces/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_workspace_member(
    workspace_id: int,
    member_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    manager = _require_manager(workspace_id, current_user, db)
    target = db.query(WorkspaceMember).filter(
        WorkspaceMember.id == member_id,
        WorkspaceMember.workspace_id == workspace_id,
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="العضو غير موجود")
    if target.role == WorkspaceRole.owner:
        raise HTTPException(status_code=403, detail="لا يمكن إزالة مالك مساحة العمل")
    if manager.role == WorkspaceRole.admin and target.role != WorkspaceRole.member:
        raise HTTPException(status_code=403, detail="المدير لا يمكنه إزالة مدير آخر")
    db.delete(target)
    db.commit()


@router.post("/workspace-invitations/accept", response_model=WorkspaceInvitationAcceptOut)
def accept_workspace_invitation(
    payload: WorkspaceInvitationAccept,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    invitation = db.query(WorkspaceInvitation).filter(
        WorkspaceInvitation.token_hash == _hash_token(payload.token),
        WorkspaceInvitation.accepted_at.is_(None),
        WorkspaceInvitation.revoked_at.is_(None),
    ).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="الدعوة غير موجودة أو تم إلغاؤها")
    if invitation.expires_at <= now:
        raise HTTPException(status_code=410, detail="انتهت صلاحية الدعوة")
    if invitation.invited_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="هذه الدعوة مرتبطة بحساب آخر")

    if db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == invitation.workspace_id,
        WorkspaceMember.user_id == current_user.id,
    ).first():
        raise HTTPException(status_code=409, detail="أنت عضو بالفعل في مساحة العمل")

    db.add(
        WorkspaceMember(
            workspace_id=invitation.workspace_id,
            user_id=current_user.id,
            role=invitation.role,
        )
    )
    invitation.accepted_at = now
    db.commit()

    workspace = db.get(Workspace, invitation.workspace_id)
    if workspace:
        notify(
            db,
            workspace.owner_id,
            "تم قبول دعوة مساحة العمل",
            f"انضم {current_user.email} إلى {workspace.name}.",
            "workspace_member_joined",
        )

    return WorkspaceInvitationAcceptOut(
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        role=invitation.role,
    )
