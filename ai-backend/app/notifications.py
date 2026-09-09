"""
خدمة الإشعارات: تسجيل بقاعدة البيانات دائمًا (لمركز الإشعارات)، وبث فوري عبر WebSocket
لو المستخدم متصل وقتها.

ملاحظة: ConnectionManager هنا في الذاكرة — يشتغل تمام لنسخة واحدة من التطبيق (مثل إعداد
docker-compose الحالي). لو صار عندك أكتر من نسخة (تحجيم أفقي)، تحتاج Redis pub/sub بدلها
عشان الإشعار يوصل بغض النظر عن أي نسخة المستخدم متصل فيها.
"""
from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models.notification import Notification

logger = get_logger("notifications")


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        connections = self.active_connections.get(user_id, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections and user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_to_user(self, user_id: int, message: dict) -> None:
        for ws in list(self.active_connections.get(user_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                logger.warning("فشل إرسال إشعار فوري لمستخدم %s — الاتصال ممكن يكون انقطع", user_id)


manager = ConnectionManager()


def notify(
    db: Session, user_id: int, title: str, body: str, notification_type: str = "info"
) -> Notification:
    """يسجّل الإشعار بقاعدة البيانات — يشتغل بأي سياق (sync أو async)"""
    notification = Notification(
        user_id=user_id, title=title, body=body, notification_type=notification_type
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


async def push_realtime(notification: Notification) -> None:
    """يبث الإشعار فوريًا عبر WebSocket — استخدمها فقط من سياق async"""
    await manager.send_to_user(
        notification.user_id,
        {
            "id": notification.id,
            "title": notification.title,
            "body": notification.body,
            "notification_type": notification.notification_type,
            "created_at": notification.created_at.isoformat(),
        },
    )


async def notify_realtime(
    db: Session, user_id: int, title: str, body: str, notification_type: str = "info"
) -> Notification:
    """يسجّل الإشعار ويبثّه فوريًا بنفس الوقت — للاستخدام من سياق async فقط"""
    notification = notify(db, user_id, title, body, notification_type)
    await push_realtime(notification)
    return notification
