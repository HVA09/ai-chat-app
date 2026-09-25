"""
طبقة الاتصال بمحرك الذكاء الاصطناعي — تفوّض لأي مزوّد مضبوط في AI_PROVIDER
(openai, anthropic, gemini, deepseek). راجع app/services/ai_providers/
"""
from collections.abc import AsyncIterator, Callable
import time

import httpx
from fastapi import HTTPException, status

from app.config import settings
from app.logging_config import get_logger

from app.services.ai_providers.base import AIReply
from app.services.ai_providers.openai_provider import OpenAICompatibleProvider
from app.services.ai_providers.factory import get_provider


_RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}
logger = get_logger("ai_service")


def _is_retryable_provider_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.RequestError):
        return True
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code in _RETRYABLE_STATUS_CODES
    )



def _provider_error_status(exc: Exception) -> int | None:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    return None

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
        validate_model=False,
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


async def get_ai_reply(
    message: str,
    history: list[dict[str, str]] | None = None,
    model: str | None = None,
) -> AIReply:
    """رد كامل مع تسجيل المزوّد الذي نجح فعليًا."""
    provider = get_provider(model)
    primary_provider_name = settings.AI_PROVIDER.strip().lower()
    started_at = time.perf_counter()
    try:
        reply = await provider.get_reply(message, history)
        reply.provider = primary_provider_name
        reply.latency_ms = max(0, round((time.perf_counter() - started_at) * 1000))
        return reply
    except Exception as primary_exc:
        primary_latency_ms = max(0, round((time.perf_counter() - started_at) * 1000))
        retryable = _is_retryable_provider_error(primary_exc)
        logger.warning(
            "AI primary provider failed provider=%s retryable=%s status_code=%s latency_ms=%s",
            primary_provider_name,
            retryable,
            _provider_error_status(primary_exc),
            primary_latency_ms,
        )
        if not retryable:
            _raise_ai_http_error(primary_exc)

        fallback = _get_fallback_provider(model)
        if fallback is None:
            logger.warning(
                "AI failover unavailable primary_provider=%s latency_ms=%s",
                primary_provider_name,
                primary_latency_ms,
            )
            _raise_ai_http_error(primary_exc)

        fallback_provider_name = settings.AI_FALLBACK_PROVIDER.strip().lower()
        fallback_started_at = time.perf_counter()
        logger.info(
            "AI failover starting primary_provider=%s fallback_provider=%s",
            primary_provider_name,
            fallback_provider_name,
        )
        try:
            reply = await fallback.get_reply(message, history)
            reply.provider = fallback_provider_name
            reply.latency_ms = max(0, round((time.perf_counter() - started_at) * 1000))
            logger.info(
                "AI fallback provider succeeded fallback_provider=%s fallback_latency_ms=%s total_latency_ms=%s",
                fallback_provider_name,
                max(0, round((time.perf_counter() - fallback_started_at) * 1000)),
                reply.latency_ms,
            )
            return reply
        except Exception as fallback_exc:
            fallback_latency_ms = max(0, round((time.perf_counter() - fallback_started_at) * 1000))
            logger.warning(
                "AI fallback provider failed fallback_provider=%s retryable=%s status_code=%s latency_ms=%s",
                fallback_provider_name,
                _is_retryable_provider_error(fallback_exc),
                _provider_error_status(fallback_exc),
                fallback_latency_ms,
            )
            _raise_ai_http_error(fallback_exc)


async def stream_ai_reply(
    message: str,
    history: list[dict[str, str]] | None = None,
    model: str | None = None,
    on_provider_selected: Callable[[str], None] | None = None,
) -> AsyncIterator[str]:
    """رد يُبَث تدريجيًا — تُستخدم في /chat/stream. الأخطاء تُترك للمستدعي يمسكها
    لأنها تصير أثناء البث نفسه (بعد ما الاستجابة بدأت)، مو قبل إرسالها."""
    provider = get_provider(model)
    primary_provider_name = settings.AI_PROVIDER.strip().lower()
    stream_started_at = time.perf_counter()
    emitted = False
    primary_error: Exception | None = None

    try:
        async for chunk in provider.stream_reply(message, history):
            emitted = True
            if on_provider_selected is not None:
                on_provider_selected(primary_provider_name)
                on_provider_selected = None
            yield chunk
        logger.info(
            "AI streaming provider succeeded provider=%s latency_ms=%s",
            primary_provider_name,
            max(0, round((time.perf_counter() - stream_started_at) * 1000)),
        )
        return
    except Exception as exc:
        # بعد إرسال أول chunk لا ننتقل لمزوّد ثانٍ، حتى لا نكرر جزءًا من الرد.
        retryable = _is_retryable_provider_error(exc)
        logger.warning(
            "AI streaming primary provider failed provider=%s emitted=%s retryable=%s status_code=%s latency_ms=%s",
            primary_provider_name,
            emitted,
            retryable,
            _provider_error_status(exc),
            max(0, round((time.perf_counter() - stream_started_at) * 1000)),
        )
        if emitted or not retryable:
            raise
        primary_error = exc

    fallback = _get_fallback_provider(model)
    if fallback is None:
        assert primary_error is not None
        logger.warning(
            "AI streaming failover unavailable primary_provider=%s latency_ms=%s",
            primary_provider_name,
            max(0, round((time.perf_counter() - stream_started_at) * 1000)),
        )
        raise primary_error

    fallback_provider_name = settings.AI_FALLBACK_PROVIDER.strip().lower()
    logger.info(
        "AI streaming failover starting primary_provider=%s fallback_provider=%s",
        primary_provider_name,
        fallback_provider_name,
    )
    try:
        async for chunk in fallback.stream_reply(message, history):
            if on_provider_selected is not None:
                on_provider_selected(fallback_provider_name)
                on_provider_selected = None
            yield chunk
        logger.info(
            "AI streaming fallback provider succeeded fallback_provider=%s latency_ms=%s",
            fallback_provider_name,
            max(0, round((time.perf_counter() - stream_started_at) * 1000)),
        )


async def get_ai_vision_reply(
    message: str,
    image_data_url: str,
    history: list[dict] | None = None,
    model: str | None = None,
) -> AIReply:
    """رد متعدد الوسائط لصورة واحدة عبر المزوّد المتوافق مع OpenAI."""
    provider = get_provider(model)
    started_at = time.perf_counter()
    if not isinstance(provider, OpenAICompatibleProvider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="تحليل الصور غير مدعوم مع مزوّد الذكاء الاصطناعي الحالي",
        )
    try:
        reply = await provider.get_vision_reply(message, image_data_url, history)
        reply.provider = settings.AI_PROVIDER.strip().lower()
        reply.latency_ms = max(0, round((time.perf_counter() - started_at) * 1000))
        return reply
    except Exception as primary_exc:
        primary_provider_name = settings.AI_PROVIDER.strip().lower()
        retryable = _is_retryable_provider_error(primary_exc)
        logger.warning(
            "AI vision primary provider failed provider=%s retryable=%s status_code=%s latency_ms=%s",
            primary_provider_name,
            retryable,
            _provider_error_status(primary_exc),
            max(0, round((time.perf_counter() - started_at) * 1000)),
        )
        if not retryable:
            _raise_ai_http_error(primary_exc)

        fallback = _get_fallback_provider(model)
        if not isinstance(fallback, OpenAICompatibleProvider):
            logger.warning(
                "AI vision failover unavailable primary_provider=%s",
                primary_provider_name,
            )
            _raise_ai_http_error(primary_exc)

        fallback_provider_name = settings.AI_FALLBACK_PROVIDER.strip().lower()
        fallback_started_at = time.perf_counter()
        logger.info(
            "AI vision failover starting primary_provider=%s fallback_provider=%s",
            primary_provider_name,
            fallback_provider_name,
        )
        try:
            reply = await fallback.get_vision_reply(message, image_data_url, history)
            reply.provider = fallback_provider_name
            reply.latency_ms = max(0, round((time.perf_counter() - started_at) * 1000))
            logger.info(
                "AI vision fallback provider succeeded fallback_provider=%s fallback_latency_ms=%s total_latency_ms=%s",
                fallback_provider_name,
                max(0, round((time.perf_counter() - fallback_started_at) * 1000)),
                reply.latency_ms,
            )
            return reply
        except Exception as fallback_exc:
            logger.warning(
                "AI vision fallback provider failed fallback_provider=%s retryable=%s status_code=%s latency_ms=%s",
                fallback_provider_name,
                _is_retryable_provider_error(fallback_exc),
                _provider_error_status(fallback_exc),
                max(0, round((time.perf_counter() - fallback_started_at) * 1000)),
            )
            _raise_ai_http_error(fallback_exc)
