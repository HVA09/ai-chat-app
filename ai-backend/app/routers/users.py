"""
مسارات بيانات المستخدم: عرض الملف الشخصي، تعديله، تغيير كلمة المرور، حذف الحساب
"""
from pathlib import Path
import json
import shutil
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.security import hash_password, verify_password
from app.audit import log_event
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.api_key import APIKey
from app.models.assistant import Assistant
from app.models.conversation import Conversation
from app.models.conversation_folder import ConversationFolder
from app.models.conversation_tag import ConversationTag
from app.models.file_attachment import FileAttachment
from app.models.project import WorkspaceProject
from app.models.project_memory import ProjectMemory
from app.models.saved_prompt import SavedPrompt
from app.models.user import User
from app.models.user_memory import UserMemory
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.user import ChangePasswordRequest, DeleteAccountRequest, ProfileUpdate, UserOut

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/me/export")
def export_account_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export the user's core application data without secrets or credentials."""
    def dt(value):
        return value.astimezone(timezone.utc).isoformat() if value else None

    conversations = (
        db.query(Conversation)
        .order_by(Conversation.created_at.asc(), Conversation.id.asc())
        .filter(Conversation.user_id == current_user.id)
        .all()
    )
    folders = (
        db.query(ConversationFolder)
        .filter(ConversationFolder.user_id == current_user.id)
        .order_by(ConversationFolder.created_at.asc(), ConversationFolder.id.asc())
        .all()
    )
    projects = (
        db.query(WorkspaceProject)
        .filter(WorkspaceProject.owner_id == current_user.id)
        .order_by(WorkspaceProject.created_at.asc(), WorkspaceProject.id.asc())
        .all()
    )
    assistants = (
        db.query(Assistant)
        .filter(Assistant.user_id == current_user.id)
        .order_by(Assistant.created_at.asc(), Assistant.id.asc())
        .all()
    )
    saved_prompts = (
        db.query(SavedPrompt)
        .filter(SavedPrompt.user_id == current_user.id)
        .order_by(SavedPrompt.created_at.asc(), SavedPrompt.id.asc())
        .all()
    )
    memories = (
        db.query(UserMemory)
        .filter(UserMemory.user_id == current_user.id)
        .order_by(UserMemory.created_at.asc(), UserMemory.id.asc())
        .all()
    )
    project_memories = (
        db.query(ProjectMemory)
        .filter(ProjectMemory.created_by_user_id == current_user.id)
        .order_by(ProjectMemory.created_at.asc(), ProjectMemory.id.asc())
        .all()
    )
    tags = (
        db.query(ConversationTag)
        .filter(ConversationTag.user_id == current_user.id)
        .order_by(ConversationTag.created_at.asc(), ConversationTag.id.asc())
        .all()
    )
    api_keys = (
        db.query(APIKey)
        .filter(APIKey.user_id == current_user.id)
        .order_by(APIKey.created_at.asc(), APIKey.id.asc())
        .all()
    )
    files = (
        db.query(FileAttachment)
        .filter(FileAttachment.user_id == current_user.id)
        .order_by(FileAttachment.created_at.asc(), FileAttachment.id.asc())
        .all()
    )
    memberships = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.user_id == current_user.id)
        .order_by(WorkspaceMember.created_at.asc(), WorkspaceMember.id.asc())
        .all()
    )
    owned_workspaces = (
        db.query(Workspace)
        .filter(Workspace.owner_id == current_user.id)
        .order_by(Workspace.created_at.asc(), Workspace.id.asc())
        .all()
    )

    workspace_by_id = {item.id: item for item in owned_workspaces}
    if memberships:
        member_workspace_ids = [membership.workspace_id for membership in memberships]
        for workspace in (
            db.query(Workspace)
            .filter(Workspace.id.in_(member_workspace_ids))
            .all()
        ):
            workspace_by_id[workspace.id] = workspace

    conversation_data = []
    for conversation in conversations:
        conversation_data.append(
            {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": dt(conversation.created_at),
                "updated_at": dt(conversation.updated_at),
                "is_pinned": conversation.is_pinned,
                "is_archived": conversation.is_archived,
                "folder_id": conversation.folder_id,
                "project_id": conversation.project_id,
                "assistant_id": conversation.assistant_id,
                "workspace_id": conversation.workspace_id,
                "ai_model": conversation.ai_model,
                "deleted_at": dt(conversation.deleted_at),
                "summary": conversation.summary,
                "summary_updated_at": dt(conversation.summary_updated_at),
                "parent_conversation_id": conversation.parent_conversation_id,
                "branched_from_message_index": conversation.branched_from_message_index,
                "tags": [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in conversation.tags],
                "messages": [
                    {
                        "id": message.id,
                        "role": message.role.value,
                        "content": message.content,
                        "created_at": dt(message.created_at),
                        "sources": message.sources or [],
                        "feedback": message.feedback,
                        "is_bookmarked": message.is_bookmarked,
                    }
                    for message in conversation.messages
                ],
            }
        )

    payload = {
        "schema_version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role.value,
            "is_active": current_user.is_active,
            "is_email_verified": current_user.is_email_verified,
            "is_2fa_enabled": current_user.is_2fa_enabled,
            "full_name": current_user.full_name,
            "avatar_url": current_user.avatar_url,
            "created_at": dt(current_user.created_at),
        },
        "workspaces": [
            {
                "id": workspace.id,
                "name": workspace.name,
                "owner_id": workspace.owner_id,
                "default_ai_model": workspace.default_ai_model,
                "daily_ai_request_limit": workspace.daily_ai_request_limit,
                "created_at": dt(workspace.created_at),
                "membership_role": next(
                    (
                        membership.role.value
                        for membership in memberships
                        if membership.workspace_id == workspace.id
                    ),
                    "owner" if workspace.owner_id == current_user.id else None,
                ),
            }
            for workspace in sorted(
                workspace_by_id.values(), key=lambda item: (item.created_at, item.id)
            )
        ],
        "folders": [
            {
                "id": folder.id,
                "name": folder.name,
                "workspace_id": folder.workspace_id,
                "color": folder.color,
                "sort_order": folder.sort_order,
                "created_at": dt(folder.created_at),
            }
            for folder in folders
        ],
        "projects": [
            {
                "id": project.id,
                "workspace_id": project.workspace_id,
                "assistant_id": project.assistant_id,
                "name": project.name,
                "description": project.description,
                "instructions": project.instructions,
                "created_at": dt(project.created_at),
            }
            for project in projects
        ],
        "project_memories": [
            {
                "id": item.id,
                "project_id": item.project_id,
                "content": item.content,
                "created_at": dt(item.created_at),
                "updated_at": dt(item.updated_at),
            }
            for item in project_memories
        ],
        "assistants": [
            {
                "id": assistant.id,
                "name": assistant.name,
                "description": assistant.description,
                "instructions": assistant.instructions,
                "created_at": dt(assistant.created_at),
            }
            for assistant in assistants
        ],
        "saved_prompts": [
            {
                "id": prompt.id,
                "name": prompt.name,
                "content": prompt.content,
                "created_at": dt(prompt.created_at),
                "updated_at": dt(prompt.updated_at),
            }
            for prompt in saved_prompts
        ],
        "memories": [
            {
                "id": memory.id,
                "content": memory.content,
                "created_at": dt(memory.created_at),
                "updated_at": dt(memory.updated_at),
            }
            for memory in memories
        ],
        "tags": [
            {
                "id": tag.id,
                "name": tag.name,
                "color": tag.color,
                "created_at": dt(tag.created_at),
            }
            for tag in tags
        ],
        "api_keys": [
            {
                "id": key.id,
                "name": key.name,
                "key_prefix": key.key_prefix,
                "created_at": dt(key.created_at),
                "last_used_at": dt(key.last_used_at),
                "revoked_at": dt(key.revoked_at),
                "daily_request_limit": key.daily_request_limit,
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            }
            for key in api_keys
        ],
        "files": [
            {
                "id": file.id,
                "original_filename": file.original_filename,
                "content_type": file.content_type,
                "size_bytes": file.size_bytes,
                "workspace_id": file.workspace_id,
                "project_id": file.project_id,
                "created_at": dt(file.created_at),
                "extracted_text": file.extracted_text,
            }
            for file in files
        ],
        "conversations": conversation_data,
        "privacy_note": "Secrets, passwords, TOTP seeds, API key secrets, stored file binaries, and authentication tokens are intentionally excluded.",
    }

    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    filename = f"ai-chat-account-export-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/me", response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="كلمة المرور الحالية غير صحيحة"
        )
    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    log_event(db, "password_changed", f"تغيير كلمة مرور: {current_user.email}", current_user.id)
    return {"detail": "تم تغيير كلمة المرور بنجاح"}


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    payload: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="كلمة المرور غير صحيحة"
        )
    log_event(db, "account_deleted", f"حذف حساب: {current_user.email}", current_user.id)

    # الحذف بالـ DB (cascade) يشيل صفوف الملفات، لكن ما يحذف الملفات الفعلية من القرص
    user_upload_dir = Path(settings.UPLOAD_DIR) / str(current_user.id)
    shutil.rmtree(user_upload_dir, ignore_errors=True)

    db.delete(current_user)  # cascade يحذف محادثاته وسجلات استخدامه تلقائيًا
    db.commit()
