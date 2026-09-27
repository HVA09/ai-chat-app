"""Optional MCP client integration for the Agent Platform (D2)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from mcp import Client
from mcp.types import TextContent

from app.config import settings
from app.services.tools.registry import ToolContext, ToolResult, ToolSpec

logger = logging.getLogger(__name__)


class MCPIntegrationError(ValueError):
    """User-safe error raised for invalid MCP configuration."""


@dataclass(frozen=True, slots=True)
class MCPServerConfig:
    name: str
    url: str
    enabled: bool = True


def _load_server_configs() -> list[MCPServerConfig]:
    try:
        raw = json.loads(settings.MCP_SERVERS_JSON)
    except json.JSONDecodeError as exc:
        raise MCPIntegrationError("MCP server configuration is invalid JSON.") from exc

    if not isinstance(raw, list):
        raise MCPIntegrationError("MCP server configuration must be a JSON list.")

    configs: list[MCPServerConfig] = []
    for item in raw[: settings.MCP_MAX_SERVERS]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        url = str(item.get("url") or "").strip()
        enabled = bool(item.get("enabled", True))
        if not name or not url or not enabled:
            continue
        if not re.match(r"^https?://[^\s]+$", url, flags=re.IGNORECASE):
            raise MCPIntegrationError(f"Invalid MCP server URL for '{name}'.")
        if settings.ENVIRONMENT == "production" and not url.lower().startswith("https://"):
            raise MCPIntegrationError(
                f"MCP server '{name}' must use HTTPS in production."
            )
        configs.append(MCPServerConfig(name=name, url=url, enabled=enabled))

    return configs


def _safe_tool_name(server_name: str, tool_name: str) -> str:
    raw = f"mcp__{server_name}__{tool_name}".lower()
    sanitized = re.sub(r"[^a-z0-9_]+", "_", raw).strip("_")
    return sanitized[:96]


def _tool_schema(tool: Any) -> dict:
    schema = getattr(tool, "input_schema", None)
    if isinstance(schema, dict):
        return schema
    schema = getattr(tool, "inputSchema", None)
    if isinstance(schema, dict):
        return schema
    return {"type": "object", "properties": {}}


def _format_tool_result(result: Any) -> str:
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False)

    parts: list[str] = []
    for block in getattr(result, "content", []) or []:
        if isinstance(block, TextContent):
            parts.append(block.text)
            continue
        text = getattr(block, "text", None)
        if text:
            parts.append(str(text))
            continue
        uri = getattr(block, "uri", None)
        if uri:
            parts.append(str(uri))

    if parts:
        return "\n".join(parts)
    return "أعاد خادم MCP نتيجة بدون محتوى نصي."


async def _call_remote_tool(
    server: MCPServerConfig,
    remote_name: str,
    arguments: dict[str, Any],
) -> ToolResult:
    try:
        async with Client(server.url) as client:
            result = await client.call_tool(remote_name, arguments)
    except Exception as exc:
        logger.warning(
            "MCP tool call failed server=%s tool=%s error=%s",
            server.name,
            remote_name,
            exc,
        )
        return ToolResult(
            content=f"تعذر الاتصال بأداة MCP '{remote_name}' على الخادم '{server.name}'.",
            sources=[],
            succeeded=False,
        )

    content = _format_tool_result(result)
    is_error = bool(getattr(result, "is_error", False))
    return ToolResult(
        content=content,
        sources=[],
        succeeded=not is_error,
    )


async def discover_mcp_tools() -> list[ToolSpec]:
    """Discover configured MCP tools and expose them as local registry specs."""
    if not settings.MCP_ENABLED:
        return []

    specs: list[ToolSpec] = []
    for server in _load_server_configs():
        try:
            async with Client(server.url) as client:
                result = await client.list_tools()
        except Exception as exc:
            logger.warning(
                "MCP discovery failed server=%s url=%s error=%s",
                server.name,
                server.url,
                exc,
            )
            continue

        remote_tools = list(getattr(result, "tools", []) or [])[
            : settings.MCP_MAX_TOOLS_PER_SERVER
        ]
        for remote_tool in remote_tools:
            remote_name = str(getattr(remote_tool, "name", "") or "").strip()
            if not remote_name:
                continue

            description = str(
                getattr(remote_tool, "description", None)
                or f"MCP tool from {server.name}."
            ).strip()
            registry_name = _safe_tool_name(server.name, remote_name)

            async def handler(
                arguments: dict[str, Any],
                context: ToolContext,
                *,
                _server: MCPServerConfig = server,
                _remote_name: str = remote_name,
            ) -> ToolResult:
                del context
                return await _call_remote_tool(_server, _remote_name, arguments)

            specs.append(
                ToolSpec(
                    name=registry_name,
                    description=f"[MCP:{server.name}] {description}",
                    parameters=_tool_schema(remote_tool),
                    handler=handler,
                )
            )

    return specs
