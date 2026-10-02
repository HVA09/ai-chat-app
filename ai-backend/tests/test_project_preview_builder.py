import pytest

from app.config import settings
from app.schemas.project_preview import PreviewBuildFile
from app.services.project_preview_builder import (
    PreviewBuilderError,
    build_javascript_preview,
)


@pytest.mark.anyio
async def test_preview_builder_fails_closed_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "PREVIEW_BUILDER_URL", "")
    monkeypatch.setattr(settings, "PREVIEW_BUILDER_TOKEN", "")

    with pytest.raises(PreviewBuilderError, match="غير مهيأة"):
        await build_javascript_preview(
            1,
            [PreviewBuildFile(path="package.json", content='{"name":"demo"}')],
        )


@pytest.mark.anyio
async def test_preview_builder_rejects_secret_files(monkeypatch):
    monkeypatch.setattr(settings, "PREVIEW_BUILDER_URL", "http://builder.test")
    monkeypatch.setattr(settings, "PREVIEW_BUILDER_TOKEN", "test-token")
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")

    with pytest.raises(PreviewBuilderError, match="أسرار"):
        await build_javascript_preview(
            1,
            [
                PreviewBuildFile(path="package.json", content='{"name":"demo"}'),
                PreviewBuildFile(path=".env", content="API_KEY=secret"),
            ],
        )


@pytest.mark.anyio
async def test_preview_builder_posts_only_allowlisted_build_request(monkeypatch):
    monkeypatch.setattr(settings, "PREVIEW_BUILDER_URL", "http://builder.test")
    monkeypatch.setattr(settings, "PREVIEW_BUILDER_TOKEN", "test-token")
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")

    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "entrypoint": "dist/index.html",
                "artifact_base64": "YQ==",
                "artifact_size_bytes": 1,
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs["timeout"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json, headers):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(
        "app.services.project_preview_builder.httpx.AsyncClient",
        FakeClient,
    )

    result = await build_javascript_preview(
        7,
        [
            PreviewBuildFile(path="package.json", content='{"name":"demo","scripts":{"build":"vite build"}}'),
            PreviewBuildFile(path="src/main.jsx", content="export default 1;"),
        ],
    )

    assert result.entrypoint == "dist/index.html"
    assert result.artifact_size_bytes == 1
    assert captured["url"] == "http://builder.test/v1/build"
    assert captured["headers"]["Authorization"] == "Bearer test-token"
    assert captured["headers"]["X-Preview-Protocol"] == "1"
    assert captured["json"]["project_id"] == 7
    assert captured["json"]["build_command"] == "npm run build"
    assert [item["path"] for item in captured["json"]["files"]] == [
        "package.json",
        "src/main.jsx",
    ]
