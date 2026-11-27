import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from app.services import mcp_client
from app.services.mcp_client import MCPIntegrationError, _load_server_configs, discover_mcp_tools


def test_mcp_servers_are_disabled_by_default(monkeypatch):
    monkeypatch.setattr(mcp_client.settings, "MCP_ENABLED", False)
    assert asyncio.run(discover_mcp_tools()) == []


def test_mcp_server_config_requires_valid_json(monkeypatch):
    monkeypatch.setattr(mcp_client.settings, "MCP_SERVERS_JSON", "{bad")
    with pytest.raises(MCPIntegrationError, match="invalid JSON"):
        _load_server_configs()


class FakeClient:
    instances = []

    def __init__(self, url):
        self.url = url
        FakeClient.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def list_tools(self):
        return SimpleNamespace(
            tools=[
                SimpleNamespace(
                    name="add",
                    description="Add numbers",
                    input_schema={
                        "type": "object",
                        "properties": {"a": {"type": "number"}},
                    },
                )
            ]
        )

    async def call_tool(self, name, arguments):
        return SimpleNamespace(
            is_error=False,
            structured_content={"name": name, "arguments": arguments},
            content=[],
        )



@asynccontextmanager
async def _fake_open_mcp_client(url, client_class=FakeClient):
    async with client_class(url) as client:
        yield client



def test_open_mcp_client_uses_guarded_transport_and_disables_proxy_bypass(monkeypatch):
    captured = {}
    sentinel_transport = object()

    class FakeHTTPClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeMCPClient:
        def __init__(self, transport):
            captured["mcp_transport"] = transport

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(mcp_client.httpx2, "AsyncClient", FakeHTTPClient)
    monkeypatch.setattr(mcp_client, "SSRFGuardTransport", lambda: sentinel_transport)
    monkeypatch.setattr(
        mcp_client,
        "streamable_http_client",
        lambda url, *, http_client: (url, http_client),
    )
    monkeypatch.setattr(mcp_client, "Client", FakeMCPClient)

    async def exercise():
        async with mcp_client._open_mcp_client("https://example.test/mcp"):
            return None

    asyncio.run(exercise())
    assert captured["transport"] is sentinel_transport
    assert captured["timeout"].connect == mcp_client.MCP_DEFAULT_TIMEOUT
    assert captured["timeout"].write == mcp_client.MCP_DEFAULT_TIMEOUT
    assert captured["timeout"].pool == mcp_client.MCP_DEFAULT_TIMEOUT
    assert captured["timeout"].read == mcp_client.MCP_DEFAULT_SSE_READ_TIMEOUT
    assert captured["trust_env"] is False
    assert captured["proxy"] is None
    assert captured["follow_redirects"] is False
    assert captured["mcp_transport"][0] == "https://example.test/mcp"
    assert captured["mcp_transport"][1] is not None


def test_mcp_discovery_maps_remote_tools(monkeypatch):
    monkeypatch.setattr(mcp_client.settings, "MCP_ENABLED", True)
    monkeypatch.setattr(
        mcp_client.settings,
        "MCP_SERVERS_JSON",
        '[{"name":"demo","url":"https://example.test/mcp","enabled":true,"allowed_tools":["add"]}]',
    )
    monkeypatch.setattr(mcp_client, "_open_mcp_client", _fake_open_mcp_client)

    specs = asyncio.run(discover_mcp_tools())

    assert [spec.name for spec in specs] == ["mcp__demo__add"]
    assert specs[0].description == "[MCP:demo] Add numbers"
    assert specs[0].parameters["type"] == "object"
    assert specs[0].output_trust == "untrusted"
    assert FakeClient.instances[0].url == "https://example.test/mcp"


def test_mcp_server_url_must_use_https_in_production(monkeypatch):
    monkeypatch.setattr(mcp_client.settings, "MCP_SERVERS_JSON", '[{"name":"demo","url":"http://example.test/mcp"}]')
    monkeypatch.setattr(mcp_client.settings, "ENVIRONMENT", "production")

    with pytest.raises(MCPIntegrationError, match="must use HTTPS"):
        _load_server_configs()


def test_mcp_tool_handler_calls_remote_tool(monkeypatch):
    monkeypatch.setattr(mcp_client.settings, "MCP_ENABLED", True)
    monkeypatch.setattr(
        mcp_client.settings,
        "MCP_SERVERS_JSON",
        '[{"name":"demo","url":"https://example.test/mcp","enabled":true,"allowed_tools":["add"]}]',
    )
    monkeypatch.setattr(mcp_client, "_open_mcp_client", _fake_open_mcp_client)

    specs = asyncio.run(discover_mcp_tools())
    result = asyncio.run(specs[0].handler({"a": 2}, None))

    assert result.succeeded is True
    assert '"name": "add"' in result.content
    assert '"a": 2' in result.content


def test_mcp_tools_are_denied_without_server_allowlist(monkeypatch):
    monkeypatch.setattr(mcp_client.settings, "MCP_ENABLED", True)
    monkeypatch.setattr(
        mcp_client.settings,
        "MCP_SERVERS_JSON",
        '[{"name":"demo","url":"https://example.test/mcp","enabled":true}]',
    )
    monkeypatch.setattr(mcp_client, "_open_mcp_client", _fake_open_mcp_client)

    assert asyncio.run(discover_mcp_tools()) == []


def test_mcp_discovery_skips_tools_without_object_schema(monkeypatch):
    class MissingSchemaClient(FakeClient):
        async def list_tools(self):
            return SimpleNamespace(
                tools=[SimpleNamespace(name="broken", description="No schema")]
            )

    monkeypatch.setattr(mcp_client.settings, "MCP_ENABLED", True)
    monkeypatch.setattr(
        mcp_client.settings,
        "MCP_SERVERS_JSON",
        '[{"name":"demo","url":"https://example.test/mcp","allowed_tools":["broken"]}]',
    )
    monkeypatch.setattr(mcp_client, "_open_mcp_client", lambda url: _fake_open_mcp_client(url, MissingSchemaClient))

    assert asyncio.run(discover_mcp_tools()) == []


def test_mcp_server_config_parses_allowed_tools(monkeypatch):
    monkeypatch.setattr(
        mcp_client.settings,
        "MCP_SERVERS_JSON",
        '[{"name":"demo","url":"https://example.test/mcp","allowed_tools":["add","lookup"]}]',
    )
    config = _load_server_configs()[0]

    assert config.allowed_tools == ("add", "lookup")


def test_mcp_enabled_requires_boolean(monkeypatch):
    monkeypatch.setattr(mcp_client.settings, "MCP_SERVERS_JSON", '[{"name":"demo","url":"https://example.test","enabled":"false"}]')
    with pytest.raises(MCPIntegrationError, match="enabled must be a boolean"):
        _load_server_configs()


@pytest.mark.parametrize("url", ["https://user:pass@example.test/mcp", "https://example.test:bad/mcp", "https://example.test/mcp#fragment", "https:///missing-host"])
def test_mcp_rejects_malformed_url_shapes(monkeypatch, url):
    import json
    monkeypatch.setattr(mcp_client.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(mcp_client.settings, "MCP_SERVERS_JSON", json.dumps([{"name": "demo", "url": url}]))
    with pytest.raises(MCPIntegrationError, match="Invalid MCP server URL"):
        _load_server_configs()


@pytest.mark.parametrize(
    "payload",
    [
        '[null]',
        '[{"name":"demo","url":"https://example.test","enabled":true}, null]',
        '[{"url":"https://example.test"}]',
        '[{"name":"demo","url":12}]',
        '[{"name":"demo","url":"https://example.test","allowed_tools":["add", 7]}]',
        '[{"name":"demo","url":"https://example.test","allowed_tools":["add", " "]}]',
        '[{"name":"demo","url":"https://example.test","allowed_tools":["add", "add"]}]',
    ],
)
def test_mcp_server_config_rejects_malformed_entries_and_allowlists(monkeypatch, payload):
    monkeypatch.setattr(mcp_client.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(mcp_client.settings, "MCP_SERVERS_JSON", payload)

    with pytest.raises(MCPIntegrationError):
        _load_server_configs()


def test_mcp_server_config_rejects_server_count_over_limit(monkeypatch):
    import json

    monkeypatch.setattr(mcp_client.settings, "MCP_MAX_SERVERS", 1)
    monkeypatch.setattr(
        mcp_client.settings,
        "MCP_SERVERS_JSON",
        json.dumps([
            {"name": "first", "url": "https://first.example"},
            {"name": "second", "url": "https://second.example"},
        ]),
    )

    with pytest.raises(MCPIntegrationError, match="exceeds the maximum"):
        _load_server_configs()


def test_disabled_mcp_server_is_validated_but_not_loaded(monkeypatch):
    monkeypatch.setattr(
        mcp_client.settings,
        "MCP_SERVERS_JSON",
        '[{"name":"demo","url":"https://example.test","enabled":false,"allowed_tools":[]}]',
    )

    assert _load_server_configs() == []
