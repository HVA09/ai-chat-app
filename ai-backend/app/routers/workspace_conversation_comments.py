"""تعليقات التعاون على المحادثات المشتركة داخل مساحة العمل."""
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.conversation import Conversation, Message
from app.models.conversation_workspace_share import ConversationWorkspaceShare
from app.models.conversation_comment import ConversationComment
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.notifications import manager, notify
from app.schemas.workspace_conversation_comments import (
    ConversationCommentCreate,
    ConversationCommentOut,
    ConversationCommentUpdate,
)

router = APIRouter(tags=["Workspace Conversation Comments"])


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
        raise HTTPException(status_code=404, detail="مساحة العمل غير موجودة")
    return membership


def _get_shared_conversation(
    workspace_id: int,
    conversation_id: int,
    current_user: User,
    db: Session,
) -> Conversation:
    _get_membership(workspace_id, current_user, db)
    shared = (
        db.query(Conversation)
        .join(
            ConversationWorkspaceShare,
            ConversationWorkspaceShare.conversation_id == Conversation.id,
        )
        .filter(
            Conversation.id == conversation_id,
            Conversation.deleted_at.is_(None),
            ConversationWorkspaceShare.workspace_id == workspace_id,
        )
        .first()
    )
    if not shared:
        raise HTTPException(status_code=404, detail="المحادثة المشتركة غير موجودة")
    return shared


def _get_comment(
    workspace_id: int,
    conversation_id: int,
    comment_id: int,
    current_user: User,
    db: Session,
) -> tuple[Conversation, ConversationComment, WorkspaceMember]:
    conversation = _get_shared_conversation(
        workspace_id, conversation_id, current_user, db
    )
    comment = (
        db.query(ConversationComment)
        .filter(
            ConversationComment.id == comment_id,
            ConversationComment.conversation_id == conversation.id,
        )
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="التعليق غير موجود")
    return conversation, comment, _get_membership(workspace_id, current_user, db)


def _serialize(comment: ConversationComment, db: Session) -> ConversationCommentOut:
    author = db.get(User, comment.user_id)
    return ConversationCommentOut(
        id=comment.id,
        conversation_id=comment.conversation_id,
        user_id=comment.user_id,
        user_email=author.email if author else "",
        message_id=comment.message_id,
        content=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.get(
    "/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments",
    response_model=list[ConversationCommentOut],
)
def list_conversation_comments(
    workspace_id: int,
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_shared_conversation(
        workspace_id, conversation_id, current_user, db
    )
    comments = (
        db.query(ConversationComment)
        .filter(ConversationComment.conversation_id == conversation.id)
        .order_by(ConversationComment.created_at.asc(), ConversationComment.id.asc())
        .all()
    )
    return [_serialize(comment, db) for comment in comments]


@router.post(
    "/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments",
    response_model=ConversationCommentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation_comment(
    workspace_id: int,
    conversation_id: int,
    payload: ConversationCommentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_shared_conversation(
        workspace_id, conversation_id, current_user, db
    )

    if payload.message_id is not None:
        message = (
            db.query(Message)
            .filter(
                Message.id == payload.message_id,
                Message.conversation_id == conversation.id,
            )
            .first()
        )
        if not message:
            raise HTTPException(status_code=404, detail="الرسالة غير موجودة")

    comment = ConversationComment(
        conversation_id=conversation.id,
        user_id=current_user.id,
        message_id=payload.message_id,
        content=payload.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    preview = " ".join(payload.content.split())
    if len(preview) > 160:
        preview = preview[:157] + "..."

    member_ids = [
        row.user_id
        for row in db.query(WorkspaceMember.user_id)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id != current_user.id,
        )
        .all()
    ]

    for user_id in member_ids:
        notification = notify(
            db,
            user_id,
            "تعليق جديد على محادثة مشتركة",
            f"{current_user.email}: {preview}",
            "workspace_comment",
        )
        background_tasks.add_task(
            manager.send_to_user,
            user_id,
            {
                "id": notification.id,
                "title": notification.title,
                "body": notification.body,
                "notification_type": notification.notification_type,
                "created_at": notification.created_at.isoformat(),
            },
        )

    return _serialize(comment, db)


@router.patch(
    "/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments/{comment_id}",
    response_model=ConversationCommentOut,
)
def update_conversation_comment(
    workspace_id: int,
    conversation_id: int,
    comment_id: int,
    payload: ConversationCommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _, comment, membership = _get_comment(
        workspace_id, conversation_id, comment_id, current_user, db
    )
    if (
        comment.user_id != current_user.id
        and membership.role not in {WorkspaceRole.owner, WorkspaceRole.admin}
    ):
        raise HTTPException(status_code=403, detail="لا تملك صلاحية تعديل هذا التعليق")

    comment.content = payload.content
    comment.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(comment)
    return _serialize(comment, db)


@router.delete(
    "/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conversation_comment(
    workspace_id: int,
    conversation_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _, comment, membership = _get_comment(
        workspace_id, conversation_id, comment_id, current_user, db
    )
    if (
        comment.user_id != current_user.id
        and membership.role not in {WorkspaceRole.owner, WorkspaceRole.admin}
    ):
        raise HTTPException(status_code=403, detail="لا تملك صلاحية حذف هذا التعليق")

    db.delete(comment)
    db.commit()
