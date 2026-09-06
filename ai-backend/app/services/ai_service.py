"""
طبقة الاتصال بمحرك الذكاء الاصطناعي — تفوّض لأي مزوّد مضبوط في AI_PROVIDER
(openai, anthropic, gemini, deepseek). راجع app/services/ai_providers/
"""
from collections.abc import AsyncIterator

import httpx
from fastapi import HTTPException, status

from app.services.ai_providers.base import AIReply
from app.services.ai_providers.factory import get_provider


async def get_ai_reply(message: str, history: list[dict[str, str]] | None = None) -> AIReply:
    """رد كامل دفعة وحدة (نص + عدد توكنز لو متوفر) — تُستخدم في /chat"""
    provider = get_provider()
    try:
        return await provider.get_reply(message, history)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"خطأ من محرك الذكاء الاصطناعي: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="تعذر الوصول لمحرك الذكاء الاصطناعي",
        ) from exc


async def stream_ai_reply(
    message: str, history: list[dict[str, str]] | None = None
) -> AsyncIterator[str]:
    """رد يُبَث تدريجيًا — تُستخدم في /chat/stream. الأخطاء تُترك للمستدعي يمسكها
    لأنها تصير أثناء البث نفسه (بعد ما الاستجابة بدأت)، مو قبل إرسالها."""
    provider = get_provider()
    async for chunk in provider.stream_reply(message, history):
        yield chunk
