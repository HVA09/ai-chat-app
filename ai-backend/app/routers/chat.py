"""
مسارات المحادثة مع الذكاء الاصطناعي: عادي (/chat) ومباشر تدريجيًا (/chat/stream)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import enforce_daily_ai_limit
from app.logging_config import get_logger
from app.models.conversation import Conversation, Message, MessageRole
from app.models.usage_log import UsageLog
from app.models.user import User
from app.schemas.chat import ChatEditRequest, ChatRequest, ChatResponse
from app.services.ai_service import get_ai_reply, stream_ai_reply

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = get_logger("chat")

MAX_HISTORY_MESSAGES = 20  # يحدّ من نمو الاستعلام وتكلفة/زمن استدعاء AI بمحادثة طويلة جدًا


def _get_or_create_conversation(
    payload: ChatRequest, current_user: User, db: Session
) -> Conversation:
    if payload.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == payload.conversation_id,
                Conversation.user_id == current_user.id,
            )
            .first()
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة غير موجودة"
            )
        return conversation

    conversation = Conversation(user_id=current_user.id, title=payload.message[:50])
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def _build_history(conversation: Conversation, db: Session) -> list[dict[str, str]]:
    """يجيب آخر MAX_HISTORY_MESSAGES رسالة مباشرة من القاعدة (مش كل تاريخ المحادثة)"""
    recent_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )
    recent_messages.reverse()  # نرجّعها لترتيبها الزمني الطبيعي (الأقدم أول)
    return [{"role": m.role.value, "content": m.content} for m in recent_messages]


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(enforce_daily_ai_limit),
    db: Session = Depends(get_db),
):
    conversation = _get_or_create_conversation(payload, current_user, db)
    history = _build_history(conversation, db)

    db.add(
        Message(conversation_id=conversation.id, role=MessageRole.user, content=payload.message)
    )

    reply = await get_ai_reply(payload.message, history)

    db.add(
        Message(conversation_id=conversation.id, role=MessageRole.assistant, content=reply.text)
    )
    db.add(
        UsageLog(
            user_id=current_user.id,
            endpoint="/chat",
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
        )
    )
    db.commit()

    return ChatResponse(conversation_id=conversation.id, reply=reply.text)


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(enforce_daily_ai_limit),
    db: Session = Depends(get_db),
):
    """
    نفس /chat لكن الرد يوصل تدريجيًا (Server-Sent Events).
    أحداث SSE: conversation (رقم المحادثة) → chunk (جزء نص، مرارًا) → done | error
    الأسطر الجديدة داخل chunk تُستبدل بـ \\\n نصية عشان ما تكسر صيغة السطر الواحد لكل حدث.
    """
    conversation = _get_or_create_conversation(payload, current_user, db)
    history = _build_history(conversation, db)

    db.add(
        Message(conversation_id=conversation.id, role=MessageRole.user, content=payload.message)
    )
    db.commit()

    # FastAPI يُبقي اعتماديات الطلب حية حتى ينتهي مولّد StreamingResponse
    async def event_generator():
        yield f"event: conversation\ndata: {conversation.id}\n\n"
        full_reply = ""
        try:
            async for chunk in stream_ai_reply(payload.message, history):
                full_reply += chunk
                safe_chunk = chunk.replace("\n", "\\n")
                yield f"event: chunk\ndata: {safe_chunk}\n\n"
        except Exception:
            logger.exception("خطأ أثناء بث الرد لمحادثة %s", conversation.id)
            yield "event: error\ndata: حدث خطأ أثناء توليد الرد\n\n"
            return

        try:
            db.add(
                Message(
                    conversation_id=conversation.id,
                    role=MessageRole.assistant,
                    content=full_reply,
                )
            )
            db.add(UsageLog(user_id=current_user.id, endpoint="/chat/stream"))
            db.commit()
        except Exception:
            logger.exception("فشل حفظ رد البث لمحادثة %s", conversation.id)
            db.rollback()
            yield "event: error\ndata: تعذر حفظ الرد\n\n"
            return

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{conversation_id}/regenerate/stream")
async def regenerate_chat_stream(
    conversation_id: int,
    current_user: User = Depends(enforce_daily_ai_limit),
    db: Session = Depends(get_db),
):
    """إعادة توليد آخر رد مساعد بدون إضافة رسالة مستخدم مكررة."""
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة غير موجودة")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    if not messages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا توجد رسالة لإعادة توليدها")

    previous_assistant = messages[-1] if messages[-1].role == MessageRole.assistant else None
    user_index = len(messages) - 2 if previous_assistant else len(messages) - 1

    if user_index < 0 or messages[user_index].role != MessageRole.user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="لا توجد رسالة مستخدم لإعادة توليد الرد")

    user_message = messages[user_index]
    history_messages = messages[:user_index]
    history = [{"role": m.role.value, "content": m.content} for m in history_messages[-MAX_HISTORY_MESSAGES:]]

    async def event_generator():
        yield f"event: conversation\ndata: {conversation.id}\n\n"
        full_reply = ""
        try:
            async for chunk in stream_ai_reply(user_message.content, history):
                full_reply += chunk
                safe_chunk = chunk.replace("\n", "\\n")
                yield f"event: chunk\ndata: {safe_chunk}\n\n"
        except Exception:
            logger.exception("خطأ أثناء إعادة توليد الرد لمحادثة %s", conversation.id)
            yield "event: error\ndata: حدث خطأ أثناء إعادة توليد الرد\n\n"
            return

        try:
            if previous_assistant is not None:
                db.delete(previous_assistant)
            db.add(
                Message(
                    conversation_id=conversation.id,
                    role=MessageRole.assistant,
                    content=full_reply,
                )
            )
            db.add(UsageLog(user_id=current_user.id, endpoint="/chat/regenerate/stream"))
            db.commit()
        except Exception:
            logger.exception("فشل حفظ الرد المعاد توليده لمحادثة %s", conversation.id)
            db.rollback()
            yield "event: error\ndata: تعذر حفظ الرد الجديد\n\n"
            return

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{conversation_id}/edit/stream")
async def edit_chat_stream(
    conversation_id: int,
    payload: ChatEditRequest,
    current_user: User = Depends(enforce_daily_ai_limit),
    db: Session = Depends(get_db),
):
    """تعديل رسالة مستخدم سابقة ثم إعادة توليد بقية المحادثة من موقع التعديل."""
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحادثة غير موجودة")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    user_messages = [message for message in messages if message.role == MessageRole.user]
    if payload.message_index > len(user_messages):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="رسالة المستخدم غير موجودة")

    target_message = user_messages[payload.message_index - 1]
    target_position = messages.index(target_message)
    history_messages = messages[:target_position]
    history = [{"role": m.role.value, "content": m.content} for m in history_messages[-MAX_HISTORY_MESSAGES:]]

    async def event_generator():
        yield f"event: conversation\ndata: {conversation.id}\n\n"
        full_reply = ""
        try:
            async for chunk in stream_ai_reply(payload.message, history):
                full_reply += chunk
                safe_chunk = chunk.replace("\n", "\\n")
                yield f"event: chunk\ndata: {safe_chunk}\n\n"
        except Exception:
            logger.exception("خطأ أثناء تعديل رسالة لمحادثة %s", conversation.id)
            yield "event: error\ndata: حدث خطأ أثناء تعديل الرسالة\n\n"
            return

        try:
            for message in messages[target_position + 1:]:
                db.delete(message)

            target_message.content = payload.message
            if payload.message_index == 1:
                conversation.title = payload.message[:50]

            db.add(
                Message(
                    conversation_id=conversation.id,
                    role=MessageRole.assistant,
                    content=full_reply,
                )
            )
            db.add(UsageLog(user_id=current_user.id, endpoint="/chat/edit/stream"))
            db.commit()
        except Exception:
            logger.exception("فشل حفظ الرسالة المعدلة لمحادثة %s", conversation.id)
            db.rollback()
            yield "event: error\ndata: تعذر حفظ التعديل\n\n"
            return

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
