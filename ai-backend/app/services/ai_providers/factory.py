"""
يختار مزوّد الـ AI المناسب حسب AI_PROVIDER في الإعدادات (.env)
"""
from app.config import settings
from app.services.ai_providers.anthropic_provider import AnthropicProvider
from app.services.ai_providers.base import AIProvider
from app.services.ai_providers.openai_provider import OpenAICompatibleProvider

SUPPORTED_PROVIDERS = ("openai", "deepseek", "anthropic", "gemini")


def get_provider(model: str | None = None) -> AIProvider:
    provider_name = settings.AI_PROVIDER.lower().strip()
    selected_model = (model or settings.AI_MODEL).strip()
    if selected_model not in settings.AI_ALLOWED_MODELS:
        raise ValueError(
            f"AI_MODEL='{selected_model}' غير مسموح — الخيارات: {', '.join(settings.AI_ALLOWED_MODELS)}"
        )

    if provider_name in ("openai", "deepseek", "gemini"):
        # Gemini يدعم واجهة OpenAI-compatible، لذلك نستخدم نفس العميل
        # مع AI_API_BASE_URL الخاص بـ Gemini.
        return OpenAICompatibleProvider(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_API_BASE_URL,
            model=selected_model,
        )
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=settings.AI_API_KEY, model=selected_model)

    raise ValueError(
        f"AI_PROVIDER='{provider_name}' غير مدعوم — الخيارات: {', '.join(SUPPORTED_PROVIDERS)}"
    )
