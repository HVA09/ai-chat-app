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
from app.schemas.chat import ChatRequest, ChatResponse
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
    الأسطر الجديدة داخل chunk تُستبدل بـ \\n نصية عشان ما تكسر صيغة السطر الواحد لكل حدث.
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
