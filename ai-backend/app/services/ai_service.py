"""
طبقة الاتصال بمحرك الذكاء الاصطناعي — تفوّض لأي مزوّد مضبوط في AI_PROVIDER
(openai, anthropic, gemini, deepseek). راجع app/services/ai_providers/
"""
from collections.abc import AsyncIterator

import httpx
from fastapi import HTTPException, status

from app.config import settings

from app.services.ai_providers.base import AIReply
from app.services.ai_providers.openai_provider import OpenAICompatibleProvider
from app.services.ai_providers.factory import get_provider


_RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}


def _is_retryable_provider_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.RequestError):
        return True
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code in _RETRYABLE_STATUS_CODES
    )


def _get_fallback_provider(model: str | None = None):
    provider_name = settings.AI_FALLBACK_PROVIDER.strip().lower()
    api_key = settings.AI_FALLBACK_API_KEY.strip()
    if not provider_name or not api_key:
        return None

    fallback_model = (settings.AI_FALLBACK_MODEL or model or settings.AI_MODEL).strip()
    primary_model = (model or settings.AI_MODEL).strip()
    primary_provider = settings.AI_PROVIDER.strip().lower()

    if (
        provider_name == primary_provider
        and fallback_model == primary_model
        and api_key == settings.AI_API_KEY
        and (
            not settings.AI_FALLBACK_API_BASE_URL
            or settings.AI_FALLBACK_API_BASE_URL == settings.AI_API_BASE_URL
        )
    ):
        return None

    return get_provider(
        model=fallback_model,
        provider_name=provider_name,
        api_key=api_key,
        base_url=settings.AI_FALLBACK_API_BASE_URL or settings.AI_API_BASE_URL,
    )


def _raise_ai_http_error(exc: Exception) -> None:
    if isinstance(exc, httpx.HTTPStatusError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"خطأ من محرك الذكاء الاصطناعي: {exc.response.status_code}",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="تعذر الوصول لمحرك الذكاء الاصطناعي",
    ) from exc


async def get_ai_reply(message: str, history: list[dict[str, str]] | None = None, model: str | None = None) -> AIReply:
    """رد كامل دفعة وحدة (نص + عدد توكنز لو متوفر) — تُستخدم في /chat"""
    provider = get_provider(model)
    try:
        return await provider.get_reply(message, history)
    except Exception as primary_exc:
        if not _is_retryable_provider_error(primary_exc):
            _raise_ai_http_error(primary_exc)

        fallback = _get_fallback_provider(model)
        if fallback is None:
            _raise_ai_http_error(primary_exc)

        try:
            return await fallback.get_reply(message, history)
        except Exception as fallback_exc:
            _raise_ai_http_error(fallback_exc)


async def stream_ai_reply(
    message: str,
    history: list[dict[str, str]] | None = None,
    model: str | None = None,
) -> AsyncIterator[str]:
    """رد يُبَث تدريجيًا — تُستخدم في /chat/stream. الأخطاء تُترك للمستدعي يمسكها
    لأنها تصير أثناء البث نفسه (بعد ما الاستجابة بدأت)، مو قبل إرسالها."""
    provider = get_provider(model)
    emitted = False
    try:
        async for chunk in provider.stream_reply(message, history):
            emitted = True
            yield chunk
        return
    except Exception as primary_exc:
        # بعد إرسال أول chunk لا ننتقل لمزوّد ثانٍ، حتى لا نكرر جزءًا من الرد.
        if emitted or not _is_retryable_provider_error(primary_exc):
            raise

    fallback = _get_fallback_provider(model)
    if fallback is None:
        raise primary_exc

    async for chunk in fallback.stream_reply(message, history):
        yield chunk


async def get_ai_vision_reply(
    message: str,
    image_data_url: str,
    history: list[dict] | None = None,
    model: str | None = None,
) -> AIReply:
    """رد متعدد الوسائط لصورة واحدة عبر المزوّد المتوافق مع OpenAI."""
    provider = get_provider(model)
    if not isinstance(provider, OpenAICompatibleProvider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="تحليل الصور غير مدعوم مع مزوّد الذكاء الاصطناعي الحالي",
        )
    try:
        return await provider.get_vision_reply(message, image_data_url, history)
    except Exception as primary_exc:
        if not _is_retryable_provider_error(primary_exc):
            _raise_ai_http_error(primary_exc)

        fallback = _get_fallback_provider(model)
        if not isinstance(fallback, OpenAICompatibleProvider):
            _raise_ai_http_error(primary_exc)

        try:
            return await fallback.get_vision_reply(message, image_data_url, history)
        except Exception as fallback_exc:
            _raise_ai_http_error(fallback_exc)
