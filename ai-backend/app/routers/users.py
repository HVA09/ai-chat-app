"""
مسارات بيانات المستخدم: عرض الملف الشخصي، تعديله، تغيير كلمة المرور، حذف الحساب
"""
from pathlib import Path
import shutil

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import hash_password, verify_password
from app.audit import log_event
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import ChangePasswordRequest, DeleteAccountRequest, ProfileUpdate, UserOut

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


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
