"""
يختار مزوّد الـ AI المناسب حسب AI_PROVIDER في الإعدادات (.env)
"""
from app.config import settings
from app.services.ai_providers.anthropic_provider import AnthropicProvider
from app.services.ai_providers.base import AIProvider
from app.services.ai_providers.openai_provider import OpenAICompatibleProvider

SUPPORTED_PROVIDERS = ("openai", "deepseek", "anthropic", "gemini")


def get_provider() -> AIProvider:
    provider_name = settings.AI_PROVIDER.lower().strip()

    if provider_name in ("openai", "deepseek", "gemini"):
        # Gemini يدعم واجهة OpenAI-compatible، لذلك نستخدم نفس العميل
        # مع AI_API_BASE_URL الخاص بـ Gemini.
        return OpenAICompatibleProvider(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_API_BASE_URL,
            model=settings.AI_MODEL,
        )
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=settings.AI_API_KEY, model=settings.AI_MODEL)

    raise ValueError(
        f"AI_PROVIDER='{provider_name}' غير مدعوم — الخيارات: {', '.join(SUPPORTED_PROVIDERS)}"
    )
