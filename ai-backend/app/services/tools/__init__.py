"""أدوات آمنة يمكن للمساعد تشغيلها عند الحاجة."""

from app.services.tools.calculator import CalculatorError, calculate_expression, extract_calculator_expression
from app.services.tools.web_search import (
    WebSearchError,
    WebSearchResult,
    extract_web_search_query,
    format_web_search_response,
    search_web,
)

__all__ = [
    "CalculatorError",
    "calculate_expression",
    "extract_calculator_expression",
    "WebSearchError",
    "WebSearchResult",
    "extract_web_search_query",
    "format_web_search_response",
    "search_web",
]
