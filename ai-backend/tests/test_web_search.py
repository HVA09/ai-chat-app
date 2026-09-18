"""اختبارات أداة بحث الويب."""
from unittest.mock import AsyncMock

import pytest

from app.services.tools.web_search import (
    WebSearchError,
    WebSearchResult,
    extract_web_search_query,
    format_web_search_response,
    search_web,
)


def test_extract_web_search_query():
    assert extract_web_search_query("/search python fastapi") == "python fastapi"
    assert extract_web_search_query("/websearch latest python") == "latest python"
    assert extract_web_search_query("ما الجديد؟") is None


def test_format_web_search_response_with_sources():
    text, sources = format_web_search_response(
        "FastAPI",
        [WebSearchResult("FastAPI", "https://fastapi.tiangolo.com/", "A web framework.")],
    )
    assert "[W1]" in text
    assert sources[0]["id"] == "W1"
    assert sources[0]["url"].startswith("https://")


def test_format_web_search_response_without_results():
    text, sources = format_web_search_response("unknown", [])
    assert "unknown" in text
    assert sources[0]["filename"] == "DuckDuckGo"
    assert "duckduckgo.com" in sources[0]["url"]


@pytest.mark.asyncio
async def test_search_web_parses_instant_answer(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "Heading": "Python",
                "AbstractText": "Python is a programming language.",
                "AbstractURL": "https://www.python.org/",
                "RelatedTopics": [
                    {
                        "Text": "FastAPI documentation",
                        "FirstURL": "https://fastapi.tiangolo.com/",
                    }
                ],
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(
        "app.services.tools.web_search.httpx.AsyncClient",
        FakeClient,
    )

    results = await search_web("python")
    assert [item.url for item in results] == [
        "https://www.python.org/",
        "https://fastapi.tiangolo.com/",
    ]


@pytest.mark.asyncio
async def test_search_web_rejects_empty_query():
    with pytest.raises(WebSearchError):
        await search_web("")


@pytest.mark.asyncio
async def test_search_web_timeout(monkeypatch):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            raise __import__("httpx").TimeoutException("timeout")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "app.services.tools.web_search.httpx.AsyncClient",
        FakeClient,
    )

    with pytest.raises(WebSearchError):
        await search_web("python")
