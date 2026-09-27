from types import SimpleNamespace

import pytest

from app.services import mcp_client
from app.services.mcp_client import MCPIntegrationError, _load_server_configs, discover_mcp_tools


def test_mcp_servers_are_disabled_by_default(monkeypatch):
    monkeypatch.setattr(mcp_client.settings, "MCP_ENABLED", False)
    assert __import__("asyncio").run(discover_mcp_tools()) == []


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


def test_mcp_discovery_maps_remote_tools(monkeypatch):
    monkeypatch.setattr(mcp_client.settings, "MCP_ENABLED", True)
    monkeypatch.setattr(
        mcp_client.settings,
        "MCP_SERVERS_JSON",
        '[{"name":"demo","url":"https://example.test/mcp","enabled":true}]',
    )
    monkeypatch.setattr(mcp_client, "Client", FakeClient)

    specs = __import__("asyncio").run(discover_mcp_tools())

    assert [spec.name for spec in specs] == ["mcp__demo__add"]
    assert specs[0].description == "[MCP:demo] Add numbers"
    assert specs[0].parameters["type"] == "object"
    assert FakeClient.instances[0].url == "https://example.test/mcp"


def test_mcp_server_url_must_use_https_in_production(monkeypatch):
    monkeypatch.setattr(mcp_client.settings, "MCP_SERVERS_JSON", '[{"name":"demo","url":"http://example.test/mcp"}]')
    monkeypatch.setattr(mcp_client.settings, "ENVIRONMENT", "production")

    with pytest.raises(MCPIntegrationError, match="must use HTTPS"):
        _load_server_configs()
