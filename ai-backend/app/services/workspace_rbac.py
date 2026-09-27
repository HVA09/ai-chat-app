"""Enterprise workspace RBAC policy helpers for E6."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.models.workspace_rbac import WorkspaceRBACRole


RBAC_PERMISSIONS: tuple[str, ...] = (
    "workspace.read",
    "workspace.settings",
    "members.read",
    "members.invite",
    "members.manage",
    "rbac.manage",
    "projects.manage",
    "assistants.manage",
    "files.manage",
    "scheduled_tasks.manage",
    "billing.manage",
    "api_keys.manage",
    "webhooks.manage",
    "oauth.manage",
    "audit.read",
)

LEGACY_ROLE_PERMISSIONS: dict[WorkspaceRole, frozenset[str]] = {
    WorkspaceRole.owner: frozenset(RBAC_PERMISSIONS),
    WorkspaceRole.admin: frozenset(
        permission
        for permission in RBAC_PERMISSIONS
        if permission != "rbac.manage"
    ),
    WorkspaceRole.member: frozenset(
        {
            "workspace.read",
            "members.read",
            "audit.read",
        }
    ),
}


def get_workspace_membership(
    db: Session,
    workspace_id: int,
    user_id: int,
) -> WorkspaceMember | None:
    return (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        .first()
    )


def permissions_for_membership(
    db: Session,
    membership: WorkspaceMember,
) -> frozenset[str]:
    if membership.role == WorkspaceRole.owner:
        return LEGACY_ROLE_PERMISSIONS[WorkspaceRole.owner]

    role = membership.rbac_role
    if role is not None:
        return frozenset(item.permission for item in role.permissions)

    return LEGACY_ROLE_PERMISSIONS[membership.role]


def has_workspace_permission(
    db: Session,
    membership: WorkspaceMember,
    permission: str,
) -> bool:
    return permission in permissions_for_membership(db, membership)


def ensure_valid_permissions(permissions: list[str] | set[str] | tuple[str, ...]) -> set[str]:
    normalized = {str(item).strip() for item in permissions if str(item).strip()}
    unknown = normalized.difference(RBAC_PERMISSIONS)
    if unknown:
        raise ValueError(
            f"صلاحيات غير معروفة: {', '.join(sorted(unknown))}"
        )
    return normalized


def can_delegate_permissions(
    db: Session,
    membership: WorkspaceMember,
    permissions: set[str],
) -> bool:
    available = permissions_for_membership(db, membership)
    return permissions.issubset(available)


def require_workspace_permission(
    db: Session,
    membership: WorkspaceMember,
    permission: str,
) -> None:
    if not has_workspace_permission(db, membership, permission):
        raise PermissionError(f"Missing workspace permission: {permission}")


def role_permissions(db: Session, role: WorkspaceRBACRole) -> set[str]:
    return {item.permission for item in role.permissions}
