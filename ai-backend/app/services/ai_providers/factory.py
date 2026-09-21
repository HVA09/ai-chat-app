"""
يختار مزوّد الـ AI المناسب حسب AI_PROVIDER في الإعدادات (.env)
"""
from app.config import settings
from app.services.ai_providers.anthropic_provider import AnthropicProvider
from app.services.ai_providers.base import AIProvider
from app.services.ai_providers.openai_provider import OpenAICompatibleProvider

SUPPORTED_PROVIDERS = ("openai", "deepseek", "anthropic", "gemini")


def get_provider(
    model: str | None = None,
    provider_name: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> AIProvider:
    provider_name = (provider_name or settings.AI_PROVIDER).lower().strip()
    selected_model = (model or settings.AI_MODEL).strip()
    resolved_api_key = api_key if api_key is not None else settings.AI_API_KEY
    resolved_base_url = base_url if base_url is not None and base_url.strip() else settings.AI_API_BASE_URL
    allowed_models = set(settings.AI_ALLOWED_MODELS or [])
    allowed_models.add(settings.AI_MODEL)
    if selected_model not in allowed_models:
        raise ValueError(
            f"AI_MODEL='{selected_model}' غير مسموح — الخيارات: {', '.join(settings.AI_ALLOWED_MODELS)}"
        )

    if provider_name in ("openai", "deepseek", "gemini"):
        # Gemini يدعم واجهة OpenAI-compatible، لذلك نستخدم نفس العميل
        # مع AI_API_BASE_URL الخاص بـ Gemini.
        return OpenAICompatibleProvider(
            api_key=resolved_api_key,
            base_url=resolved_base_url,
            model=selected_model,
        )
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=resolved_api_key, model=selected_model)

    raise ValueError(
        f"AI_PROVIDER='{provider_name}' غير مدعوم — الخيارات: {', '.join(SUPPORTED_PROVIDERS)}"
    )
