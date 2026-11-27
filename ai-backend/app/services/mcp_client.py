"""Optional MCP client integration for the Agent Platform (D2)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from urllib.parse import urlsplit
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
    allowed_tools: tuple[str, ...] = ()


def _load_server_configs() -> list[MCPServerConfig]:
    try:
        raw = json.loads(settings.MCP_SERVERS_JSON)
    except json.JSONDecodeError as exc:
        raise MCPIntegrationError("MCP server configuration is invalid JSON.") from exc

    if not isinstance(raw, list):
        raise MCPIntegrationError("MCP server configuration must be a JSON list.")

    if len(raw) > settings.MCP_MAX_SERVERS:
        raise MCPIntegrationError(
            f"MCP server configuration exceeds the maximum of {settings.MCP_MAX_SERVERS} servers."
        )

    configs: list[MCPServerConfig] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise MCPIntegrationError(
                f"MCP server configuration entry {index} must be a JSON object."
            )
        raw_name = item.get("name")
        raw_url = item.get("url")
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise MCPIntegrationError(
                f"MCP server configuration entry {index} requires a non-empty string name."
            )
        if not isinstance(raw_url, str) or not raw_url.strip():
            raise MCPIntegrationError(
                f"MCP server configuration entry {index} requires a non-empty string URL."
            )
        name = raw_name.strip()
        url = raw_url.strip()
        raw_enabled = item.get("enabled", True)
        if not isinstance(raw_enabled, bool):
            raise MCPIntegrationError("MCP server enabled must be a boolean.")
        enabled = raw_enabled
        raw_allowed_tools = item.get("allowed_tools", [])
        if not isinstance(raw_allowed_tools, list) or any(
            not isinstance(tool_name, str) or not tool_name.strip()
            for tool_name in raw_allowed_tools
        ):
            raise MCPIntegrationError(
                f"MCP server '{name}' allowed_tools must contain only non-empty strings."
            )
        allowed_tools = tuple(tool_name.strip() for tool_name in raw_allowed_tools)
        if len(set(allowed_tools)) != len(allowed_tools):
            raise MCPIntegrationError(
                f"MCP server '{name}' allowed_tools must not contain duplicates."
            )
        if not enabled:
            continue
        try:
            parsed_url = urlsplit(url)
            _ = parsed_url.port
        except ValueError as exc:
            raise MCPIntegrationError(f"Invalid MCP server URL for '{name}'.") from exc
        if (
            parsed_url.scheme.lower() not in {"http", "https"}
            or not parsed_url.hostname
            or parsed_url.username is not None
            or parsed_url.password is not None
            or parsed_url.fragment
            or any(character.isspace() for character in url)
        ):
            raise MCPIntegrationError(f"Invalid MCP server URL for '{name}'.")
        if settings.ENVIRONMENT == "production" and parsed_url.scheme.lower() != "https":
            raise MCPIntegrationError(f"MCP server '{name}' must use HTTPS in production.")
        configs.append(
            MCPServerConfig(
                name=name,
                url=url,
                enabled=enabled,
                allowed_tools=allowed_tools,
            )
        )

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
    raise MCPIntegrationError("MCP tool is missing a valid input schema.")


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
            "MCP tool call failed server=%s tool=%s error_type=%s",
            server.name,
            remote_name,
            type(exc).__name__,
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
    registered_names: set[str] = set()
    for server in _load_server_configs():
        try:
            async with Client(server.url) as client:
                result = await client.list_tools()
        except Exception as exc:
            logger.warning(
                "MCP discovery failed server=%s error_type=%s",
                server.name,
                type(exc).__name__,
            )
            continue

        remote_tools = list(getattr(result, "tools", []) or [])[
            : settings.MCP_MAX_TOOLS_PER_SERVER
        ]
        for remote_tool in remote_tools:
            remote_name = str(getattr(remote_tool, "name", "") or "").strip()
            if not remote_name:
                continue
            if remote_name not in server.allowed_tools:
                logger.info(
                    "MCP tool denied by server allowlist server=%s tool=%s",
                    server.name,
                    remote_name,
                )
                continue

            description = str(
                getattr(remote_tool, "description", None)
                or f"MCP tool from {server.name}."
            ).strip()
            registry_name = _safe_tool_name(server.name, remote_name)
            if registry_name in registered_names:
                logger.warning(
                    "MCP tool name collision server=%s tool=%s",
                    server.name,
                    remote_name,
                )
                continue
            try:
                schema = _tool_schema(remote_tool)
            except MCPIntegrationError:
                logger.warning(
                    "MCP tool rejected due to missing schema server=%s tool=%s",
                    server.name,
                    remote_name,
                )
                continue
            if schema.get("type") != "object" or not isinstance(
                schema.get("properties"), dict
            ):
                logger.warning(
                    "MCP tool rejected due to invalid schema server=%s tool=%s",
                    server.name,
                    remote_name,
                )
                continue
            registered_names.add(registry_name)

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
                    parameters=schema,
                    handler=handler,
                    output_trust="untrusted",
                )
            )

    return specs
