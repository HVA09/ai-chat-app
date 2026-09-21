"""حساب تكلفة استخدام الذكاء الاصطناعي من أسعار قابلة للتهيئة.

الأسعار تُحفظ في AI_PRICING_JSON بصيغة:
{
  "provider:model": {
    "input_per_million_usd": 1.0,
    "output_per_million_usd": 3.0
  }
}

لا نضع أسعارًا افتراضية لمزوّدات خارجية حتى لا نعرض تقديرات مالية غير مؤكدة.
"""
import json
from typing import Any

from app.config import settings


def _load_pricing() -> dict[str, dict[str, float]]:
    raw = settings.AI_PRICING_JSON
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(parsed, dict):
        return {}

    pricing: dict[str, dict[str, float]] = {}
    for key, value in parsed.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        try:
            pricing[key.strip().lower()] = {
                "input_per_million_usd": float(value.get("input_per_million_usd", 0) or 0),
                "output_per_million_usd": float(value.get("output_per_million_usd", 0) or 0),
            }
        except (TypeError, ValueError):
            continue
    return pricing


def get_model_pricing(provider: str | None, model: str | None) -> dict[str, float] | None:
    if not provider or not model:
        return None
    pricing = _load_pricing()
    return pricing.get(f"{provider.strip().lower()}:{model.strip().lower()}")


def estimate_cost_usd(
    provider: str | None,
    model: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
) -> tuple[float | None, float | None, float | None]:
    rates = get_model_pricing(provider, model)
    if rates is None:
        return None, None, None

    input_cost = (max(input_tokens or 0, 0) / 1_000_000) * rates["input_per_million_usd"]
    output_cost = (max(output_tokens or 0, 0) / 1_000_000) * rates["output_per_million_usd"]
    return input_cost, output_cost, input_cost + output_cost
