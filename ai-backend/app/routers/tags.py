"""مسارات إدارة وسوم المحادثات."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.conversation_tag import ConversationTag
from app.models.user import User
from app.schemas.tags import TagCreate, TagOut, TagRename

router = APIRouter(prefix="/tags", tags=["Conversation Tags"])


def _get_owned_tag(tag_id: int, current_user: User, db: Session) -> ConversationTag:
    tag = (
        db.query(ConversationTag)
        .filter(
            ConversationTag.id == tag_id,
            ConversationTag.user_id == current_user.id,
        )
        .first()
    )
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الوسم غير موجود",
        )
    return tag


def _ensure_unique_name(
    name: str,
    current_user: User,
    db: Session,
    exclude_id: int | None = None,
) -> None:
    query = db.query(ConversationTag).filter(
        ConversationTag.user_id == current_user.id,
        func.lower(ConversationTag.name) == name.lower(),
    )
    if exclude_id is not None:
        query = query.filter(ConversationTag.id != exclude_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="يوجد وسم بهذا الاسم",
        )


@router.get("", response_model=list[TagOut])
def list_tags(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(ConversationTag)
        .filter(ConversationTag.user_id == current_user.id)
        .order_by(ConversationTag.created_at.asc(), ConversationTag.id.asc())
        .all()
    )


@router.post("", response_model=TagOut, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: TagCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_unique_name(payload.name, current_user, db)
    tag = ConversationTag(
        user_id=current_user.id,
        name=payload.name,
        color=payload.color.upper(),
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.patch("/{tag_id}", response_model=TagOut)
def rename_tag(
    tag_id: int,
    payload: TagRename,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tag = _get_owned_tag(tag_id, current_user, db)
    _ensure_unique_name(payload.name, current_user, db, exclude_id=tag.id)
    tag.name = payload.name
    tag.color = payload.color.upper()
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tag = _get_owned_tag(tag_id, current_user, db)
    db.delete(tag)
    db.commit()
