"""إدارة المساعدين المخصصين للمستخدم الحالي."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.assistant import Assistant
from app.models.user import User
from app.schemas.assistants import AssistantCreate, AssistantOut, AssistantUpdate

router = APIRouter(prefix="/assistants", tags=["Assistants"])


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


def _ensure_unique_name(
    name: str,
    current_user: User,
    db: Session,
    exclude_id: int | None = None,
) -> None:
    query = db.query(Assistant).filter(
        Assistant.user_id == current_user.id,
        func.lower(Assistant.name) == name.lower(),
    )
    if exclude_id is not None:
        query = query.filter(Assistant.id != exclude_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="يوجد مساعد بهذا الاسم",
        )


@router.get("", response_model=list[AssistantOut])
def list_assistants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Assistant)
        .filter(Assistant.user_id == current_user.id)
        .order_by(Assistant.created_at.asc(), Assistant.id.asc())
        .all()
    )


@router.post("", response_model=AssistantOut, status_code=status.HTTP_201_CREATED)
def create_assistant(
    payload: AssistantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_unique_name(payload.name, current_user, db)
    assistant = Assistant(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        instructions=payload.instructions,
    )
    db.add(assistant)
    db.commit()
    db.refresh(assistant)
    return assistant


@router.patch("/{assistant_id}", response_model=AssistantOut)
def update_assistant(
    assistant_id: int,
    payload: AssistantUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assistant = _get_owned_assistant(assistant_id, current_user, db)

    if payload.name is not None:
        _ensure_unique_name(payload.name, current_user, db, exclude_id=assistant.id)
        assistant.name = payload.name
    if payload.description is not None:
        assistant.description = payload.description
    if payload.instructions is not None:
        assistant.instructions = payload.instructions

    db.commit()
    db.refresh(assistant)
    return assistant


@router.delete("/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assistant(
    assistant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assistant = _get_owned_assistant(assistant_id, current_user, db)
    db.delete(assistant)
    db.commit()
