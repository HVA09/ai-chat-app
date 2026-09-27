import asyncio
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


def test_mcp_discovery_maps_remote_tools(monkeypatch):
    monkeypatch.setattr(mcp_client.settings, "MCP_ENABLED", True)
    monkeypatch.setattr(
        mcp_client.settings,
        "MCP_SERVERS_JSON",
        '[{"name":"demo","url":"https://example.test/mcp","enabled":true,"allowed_tools":["add"]}]',
    )
    monkeypatch.setattr(mcp_client, "Client", FakeClient)

    specs = asyncio.run(discover_mcp_tools())

    assert [spec.name for spec in specs] == ["mcp__demo__add"]
    assert specs[0].description == "[MCP:demo] Add numbers"
    assert specs[0].parameters["type"] == "object"
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
    monkeypatch.setattr(mcp_client, "Client", FakeClient)

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
    monkeypatch.setattr(mcp_client, "Client", FakeClient)

    assert asyncio.run(discover_mcp_tools()) == []


def test_mcp_server_config_parses_allowed_tools(monkeypatch):
    monkeypatch.setattr(
        mcp_client.settings,
        "MCP_SERVERS_JSON",
        '[{"name":"demo","url":"https://example.test/mcp","allowed_tools":["add","lookup"]}]',
    )
    config = _load_server_configs()[0]

    assert config.allowed_tools == ("add", "lookup")
