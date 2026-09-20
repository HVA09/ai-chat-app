"""مسارات الذاكرة الدائمة التي يملكها المستخدم."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.user_memory import UserMemory
from app.schemas.memories import MemoryCreate, MemoryOut, MemoryUpdate

router = APIRouter(prefix="/memories", tags=["Memories"])


def _get_owned_memory(memory_id: int, current_user: User, db: Session) -> UserMemory:
    memory = (
        db.query(UserMemory)
        .filter(
            UserMemory.id == memory_id,
            UserMemory.user_id == current_user.id,
        )
        .first()
    )
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الذاكرة غير موجودة",
        )
    return memory


@router.get("", response_model=list[MemoryOut])
def list_memories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(UserMemory)
        .filter(UserMemory.user_id == current_user.id)
        .order_by(UserMemory.updated_at.desc(), UserMemory.id.desc())
        .limit(50)
        .all()
    )


@router.post("", response_model=MemoryOut, status_code=status.HTTP_201_CREATED)
def create_memory(
    payload: MemoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memory = UserMemory(user_id=current_user.id, content=payload.content)
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


@router.patch("/{memory_id}", response_model=MemoryOut)
def update_memory(
    memory_id: int,
    payload: MemoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memory = _get_owned_memory(memory_id, current_user, db)
    memory.content = payload.content
    db.commit()
    db.refresh(memory)
    return memory


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(
    memory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memory = _get_owned_memory(memory_id, current_user, db)
    db.delete(memory)
    db.commit()
