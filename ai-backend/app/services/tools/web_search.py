"""بحث ويب بسيط وآمن عبر DuckDuckGo Instant Answers.

الأداة لا تستخدم eval/HTML scraping ولا تقبل URL يختاره المستخدم كوجهة HTTP.
هي ترسل نص الاستعلام فقط إلى endpoint ثابت، وتعيد مصادر قابلة للاقتباس.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus

import httpx

from app.config import settings


SEARCH_URL = "https://api.duckduckgo.com/"
MAX_QUERY_LENGTH = 200
DEFAULT_RESULT_LIMIT = 5


class WebSearchError(ValueError):
    """خطأ في تنفيذ بحث الويب."""


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str


def extract_web_search_query(message: str) -> str | None:
    """يرجع استعلام البحث إذا كانت الرسالة أمر بحث، وإلا None."""
    text = message.strip()
    for prefix in ("/search", "/websearch"):
        if text == prefix:
            return ""
        if text.startswith(prefix + " "):
            return text[len(prefix) + 1 :].strip()
    return None


def _clean_text(value: object, limit: int = 500) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).strip()[:limit]


def _append_result(results: list[WebSearchResult], seen_urls: set[str], item: dict) -> None:
    title = _clean_text(item.get("Text") or item.get("FirstText"), 180)
    url = item.get("FirstURL") or item.get("FirstUrl") or item.get("URL")
    snippet = _clean_text(item.get("Result") or item.get("Text"), 500)
    if not title or not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return
    if url in seen_urls:
        return
    seen_urls.add(url)
    results.append(WebSearchResult(title=title, url=url, snippet=snippet))


def _collect_related_topics(
    topics: list[dict],
    results: list[WebSearchResult],
    seen_urls: set[str],
    limit: int,
) -> None:
    for item in topics:
        if len(results) >= limit:
            return
        if "Topics" in item and isinstance(item["Topics"], list):
            _collect_related_topics(item["Topics"], results, seen_urls, limit)
        else:
            _append_result(results, seen_urls, item)


async def search_web(
    query: str,
    *,
    limit: int | None = None,
) -> list[WebSearchResult]:
    query = query.strip()
    if not query:
        raise WebSearchError("اكتب استعلام البحث بعد /search.")
    if len(query) > MAX_QUERY_LENGTH:
        raise WebSearchError("استعلام البحث طويل جدًا.")

    result_limit = max(1, min(limit or DEFAULT_RESULT_LIMIT, 8))

    try:
        async with httpx.AsyncClient(
            timeout=settings.WEB_SEARCH_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "AI-Chat-SaaS/1.0"},
        ) as client:
            response = await client.get(
                SEARCH_URL,
                params={
                    "q": query,
                    "format": "json",
                    "no_html": "1",
                    "no_redirect": "1",
                    "skip_disambig": "1",
                    "kl": "wt-wt",
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as exc:
        raise WebSearchError("انتهت مهلة البحث على الويب.") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise WebSearchError("تعذر الوصول إلى خدمة البحث.") from exc

    results: list[WebSearchResult] = []
    seen_urls: set[str] = set()

    if isinstance(payload, dict):
        abstract_url = payload.get("AbstractURL")
        if isinstance(abstract_url, str) and abstract_url.startswith(("http://", "https://")):
            results.append(
                WebSearchResult(
                    title=_clean_text(payload.get("Heading") or payload.get("AbstractText"), 180)
                    or "DuckDuckGo Instant Answer",
                    url=abstract_url,
                    snippet=_clean_text(payload.get("AbstractText"), 500),
                )
            )
            seen_urls.add(abstract_url)

        related = payload.get("RelatedTopics")
        if isinstance(related, list):
            _collect_related_topics(related, results, seen_urls, result_limit)

    return results[:result_limit]


def format_web_search_response(query: str, results: list[WebSearchResult]) -> tuple[str, list[dict]]:
    """يبني رسالة عرض + مصادر بنفس بنية مصادر RAG."""
    if not results:
        search_url = f"https://duckduckgo.com/?q={quote_plus(query)}"
        return (
            f"لم أجد نتائج فورية كافية لهذا البحث: **{query}**.\n\n"
            "يمكنك فتح صفحة البحث الكاملة من المصدر أدناه.",
            [
                {
                    "id": "W1",
                    "filename": "DuckDuckGo",
                    "url": search_url,
                    "chunk": None,
                    "kind": "web",
                }
            ],
        )

    sources: list[dict] = []
    parts = [f"نتائج البحث عن: **{query}**"]
    for index, result in enumerate(results, start=1):
        source_id = f"W{index}"
        sources.append(
            {
                "id": source_id,
                "filename": result.title,
                "url": result.url,
                "snippet": result.snippet,
                "chunk": None,
                "kind": "web",
            }
        )
        if result.snippet:
            parts.append(f"\n[{source_id}] **{result.title}**\n{result.snippet}")
        else:
            parts.append(f"\n[{source_id}] **{result.title}**")

    return "\n".join(parts), sources


__all__ = [
    "WebSearchError",
    "WebSearchResult",
    "extract_web_search_query",
    "format_web_search_response",
    "search_web",
]
