"""مسارات مكتبة الموجهات المحفوظة الخاصة بالمستخدم."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.saved_prompt import SavedPrompt
from app.models.user import User
from app.schemas.saved_prompts import SavedPromptCreate, SavedPromptOut, SavedPromptUpdate

router = APIRouter(prefix="/saved-prompts", tags=["Saved Prompts"])


def _get_owned_prompt(prompt_id: int, current_user: User, db: Session) -> SavedPrompt:
    prompt = (
        db.query(SavedPrompt)
        .filter(
            SavedPrompt.id == prompt_id,
            SavedPrompt.user_id == current_user.id,
        )
        .first()
    )
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الموجه المحفوظ غير موجود",
        )
    return prompt


def _ensure_unique_name(
    name: str,
    current_user: User,
    db: Session,
    exclude_id: int | None = None,
) -> None:
    query = db.query(SavedPrompt).filter(
        SavedPrompt.user_id == current_user.id,
        func.lower(SavedPrompt.name) == name.lower(),
    )
    if exclude_id is not None:
        query = query.filter(SavedPrompt.id != exclude_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="يوجد موجه محفوظ بهذا الاسم",
        )


@router.get("", response_model=list[SavedPromptOut])
def list_saved_prompts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(SavedPrompt)
        .filter(SavedPrompt.user_id == current_user.id)
        .order_by(SavedPrompt.updated_at.desc(), SavedPrompt.id.desc())
        .all()
    )


@router.post("", response_model=SavedPromptOut, status_code=status.HTTP_201_CREATED)
def create_saved_prompt(
    payload: SavedPromptCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_unique_name(payload.name, current_user, db)
    prompt = SavedPrompt(
        user_id=current_user.id,
        name=payload.name,
        content=payload.content,
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt


@router.patch("/{prompt_id}", response_model=SavedPromptOut)
def update_saved_prompt(
    prompt_id: int,
    payload: SavedPromptUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prompt = _get_owned_prompt(prompt_id, current_user, db)
    _ensure_unique_name(payload.name, current_user, db, exclude_id=prompt.id)
    prompt.name = payload.name
    prompt.content = payload.content
    prompt.updated_at = func.now()
    db.commit()
    db.refresh(prompt)
    return prompt


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_prompt(
    prompt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prompt = _get_owned_prompt(prompt_id, current_user, db)
    db.delete(prompt)
    db.commit()
