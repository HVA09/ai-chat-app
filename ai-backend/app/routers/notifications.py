"""
مسارات الإشعارات: عرض/تعليم كمقروء عبر REST، واتصال فوري عبر WebSocket
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.database import get_db
from app.dependencies import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.notifications import manager
from app.schemas.notification import NotificationOut

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الإشعار غير موجود")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read.is_(False)
    ).update({"is_read": True})
    db.commit()
    return {"detail": "تم تعليم كل الإشعارات كمقروءة"}


@router.websocket("/ws/notifications")
async def notifications_websocket(websocket: WebSocket, db: Session = Depends(get_db)):
    """WebSocket authenticated with the HttpOnly access-token cookie; no JWT in the URL."""
    try:
        token = websocket.cookies.get("access_token")
        if not token:
            raise ValueError("missing access cookie")
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError
        user_id = int(payload.get("sub"))
    except Exception:
        await websocket.close(code=4001)
        return

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        await websocket.close(code=4001)
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # نبقي الاتصال مفتوح؛ ما نحتاج نعالج شيء من العميل
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
