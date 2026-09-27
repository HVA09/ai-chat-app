"""Enterprise RBAC management endpoints for workspaces."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.audit import log_event
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.models.workspace_rbac import WorkspaceRBACRole, WorkspaceRBACPermission
from app.schemas.workspace_rbac import (
    WorkspaceMemberRBACRoleUpdate,
    WorkspaceRBACPermissionCatalogItem,
    WorkspaceRBACRoleCreate,
    WorkspaceRBACRoleOut,
    WorkspaceRBACRoleUpdate,
)
from app.services.workspace_rbac import (
    RBAC_PERMISSIONS,
    can_delegate_permissions,
    ensure_valid_permissions,
    get_workspace_membership,
    permissions_for_membership,
    require_workspace_permission,
    role_permissions,
)

router = APIRouter(tags=["Workspace RBAC"])

PERMISSION_DESCRIPTIONS = {
    "workspace.read": "قراءة بيانات مساحة العمل.",
    "workspace.settings": "إدارة إعدادات مساحة العمل.",
    "members.read": "عرض أعضاء مساحة العمل.",
    "members.invite": "دعوة أعضاء جدد.",
    "members.manage": "إدارة أدوار الأعضاء وإزالتهم.",
    "rbac.manage": "إنشاء وتعديل وحذف أدوار RBAC وتعيينها.",
    "projects.manage": "إدارة مشاريع مساحة العمل.",
    "assistants.manage": "إدارة المساعدين المشتركين.",
    "files.manage": "إدارة ملفات مساحة العمل.",
    "scheduled_tasks.manage": "إدارة المهام المجدولة.",
    "billing.manage": "إدارة الفوترة والاشتراكات.",
    "api_keys.manage": "إدارة مفاتيح Developer API المرتبطة بالمساحة.",
    "webhooks.manage": "إدارة Webhooks الخاصة بالمساحة.",
    "oauth.manage": "إدارة الموصلات OAuth الخاصة بالمساحة.",
    "audit.read": "قراءة سجل التدقيق.",
}


def _membership_or_404(
    workspace_id: int,
    current_user: User,
    db: Session,
) -> WorkspaceMember:
    membership = get_workspace_membership(db, workspace_id, current_user.id)
    if not membership:
        raise HTTPException(status_code=404, detail="مساحة العمل غير موجودة")
    return membership


def _require(
    workspace_id: int,
    current_user: User,
    db: Session,
    permission: str,
) -> WorkspaceMember:
    membership = _membership_or_404(workspace_id, current_user, db)
    try:
        require_workspace_permission(db, membership, permission)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"تحتاج إلى الصلاحية {permission}",
        ) from None
    return membership


def _role_out(role: WorkspaceRBACRole) -> WorkspaceRBACRoleOut:
    return WorkspaceRBACRoleOut(
        id=role.id,
        workspace_id=role.workspace_id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions=sorted(role_permissions(None, role)),
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


@router.get(
    "/workspaces/{workspace_id}/rbac/permissions",
    response_model=list[WorkspaceRBACPermissionCatalogItem],
)
def list_rbac_permissions(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require(workspace_id, current_user, db, "workspace.read")
    return [
        WorkspaceRBACPermissionCatalogItem(
            permission=permission,
            description=PERMISSION_DESCRIPTIONS.get(permission, permission),
        )
        for permission in RBAC_PERMISSIONS
    ]


@router.get(
    "/workspaces/{workspace_id}/rbac/roles",
    response_model=list[WorkspaceRBACRoleOut],
)
def list_rbac_roles(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require(workspace_id, current_user, db, "workspace.read")
    roles = (
        db.query(WorkspaceRBACRole)
        .filter(WorkspaceRBACRole.workspace_id == workspace_id)
        .order_by(WorkspaceRBACRole.name.asc())
        .all()
    )
    return [_role_out(role) for role in roles]


@router.post(
    "/workspaces/{workspace_id}/rbac/roles",
    response_model=WorkspaceRBACRoleOut,
    status_code=status.HTTP_201_CREATED,
)
def create_rbac_role(
    workspace_id: int,
    payload: WorkspaceRBACRoleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = _require(workspace_id, current_user, db, "rbac.manage")
    try:
        permissions = ensure_valid_permissions(payload.permissions)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not can_delegate_permissions(db, membership, permissions):
        raise HTTPException(
            status_code=403,
            detail="لا يمكنك منح صلاحيات أعلى من صلاحياتك الحالية",
        )

    role = WorkspaceRBACRole(
        workspace_id=workspace_id,
        name=payload.name,
        description=payload.description.strip() if payload.description else None,
        is_system=False,
        created_by_user_id=current_user.id,
    )
    for permission in sorted(permissions):
        role.permissions.append(WorkspaceRBACPermission(permission=permission))

    db.add(role)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        if "uq_workspace_rbac_roles_workspace_name" in str(exc):
            raise HTTPException(status_code=409, detail="اسم الدور مستخدم بالفعل") from exc
        raise
    db.refresh(role)

    log_event(
        db,
        "workspace_rbac_role_created",
        f"إنشاء دور RBAC {role.name}",
        current_user.id,
        workspace_id,
    )
    return _role_out(role)


@router.patch(
    "/workspaces/{workspace_id}/rbac/roles/{role_id}",
    response_model=WorkspaceRBACRoleOut,
)
def update_rbac_role(
    workspace_id: int,
    role_id: int,
    payload: WorkspaceRBACRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = _require(workspace_id, current_user, db, "rbac.manage")
    role = (
        db.query(WorkspaceRBACRole)
        .filter(
            WorkspaceRBACRole.id == role_id,
            WorkspaceRBACRole.workspace_id == workspace_id,
        )
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="دور RBAC غير موجود")
    if role.is_system:
        raise HTTPException(status_code=409, detail="لا يمكن تعديل الدور النظامي")

    if payload.permissions is not None:
        try:
            permissions = ensure_valid_permissions(payload.permissions)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not can_delegate_permissions(db, membership, permissions):
            raise HTTPException(
                status_code=403,
                detail="لا يمكنك منح صلاحيات أعلى من صلاحياتك الحالية",
            )
        role.permissions.clear()
        for permission in sorted(permissions):
            role.permissions.append(
                WorkspaceRBACPermission(permission=permission)
            )

    if payload.name is not None:
        role.name = payload.name
    if payload.description is not None:
        role.description = payload.description.strip() or None

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        if "uq_workspace_rbac_roles_workspace_name" in str(exc):
            raise HTTPException(status_code=409, detail="اسم الدور مستخدم بالفعل") from exc
        raise
    db.refresh(role)

    log_event(
        db,
        "workspace_rbac_role_updated",
        f"تحديث دور RBAC {role.name}",
        current_user.id,
        workspace_id,
    )
    return _role_out(role)


@router.delete(
    "/workspaces/{workspace_id}/rbac/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_rbac_role(
    workspace_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require(workspace_id, current_user, db, "rbac.manage")
    role = (
        db.query(WorkspaceRBACRole)
        .filter(
            WorkspaceRBACRole.id == role_id,
            WorkspaceRBACRole.workspace_id == workspace_id,
        )
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="دور RBAC غير موجود")
    if role.is_system:
        raise HTTPException(status_code=409, detail="لا يمكن حذف الدور النظامي")
    assigned = db.query(WorkspaceMember.id).filter(
        WorkspaceMember.rbac_role_id == role.id
    ).first()
    if assigned:
        raise HTTPException(
            status_code=409,
            detail="لا يمكن حذف دور RBAC ما دام معينًا لعضو",
        )
    db.delete(role)
    db.commit()
    log_event(
        db,
        "workspace_rbac_role_deleted",
        f"حذف دور RBAC {role.name}",
        current_user.id,
        workspace_id,
    )


@router.patch(
    "/workspaces/{workspace_id}/members/{member_id}/rbac-role",
    response_model=WorkspaceRBACRoleOut | None,
)
def assign_rbac_role(
    workspace_id: int,
    member_id: int,
    payload: WorkspaceMemberRBACRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = _require(workspace_id, current_user, db, "rbac.manage")

    target = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.id == member_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="العضو غير موجود")
    if target.role == WorkspaceRole.owner:
        raise HTTPException(status_code=403, detail="لا يمكن تعيين دور RBAC مخصص للمالك")

    if payload.rbac_role_id is None:
        target.rbac_role_id = None
        db.commit()
        log_event(
            db,
            "workspace_member_rbac_role_cleared",
            f"إزالة دور RBAC من العضو {target.user_id}",
            current_user.id,
            workspace_id,
        )
        return None

    role = (
        db.query(WorkspaceRBACRole)
        .filter(
            WorkspaceRBACRole.id == payload.rbac_role_id,
            WorkspaceRBACRole.workspace_id == workspace_id,
        )
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="دور RBAC غير موجود")

    permissions = role_permissions(db, role)
    if not can_delegate_permissions(db, membership, permissions):
        raise HTTPException(
            status_code=403,
            detail="لا يمكنك تعيين دور يمنح صلاحيات أعلى من صلاحياتك",
        )

    target.rbac_role_id = role.id
    db.commit()
    db.refresh(target)

    log_event(
        db,
        "workspace_member_rbac_role_assigned",
        f"تعيين دور RBAC {role.name} للعضو {target.user_id}",
        current_user.id,
        workspace_id,
    )
    return _role_out(role)
