"""Reusable execution runtime for bounded Agent Platform runs (D3)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from sqlalchemy.orm import Session

from app.config import settings
from app.models.conversation import Conversation
from app.models.user import User
from app.services.tool_security import wrap_untrusted_tool_output
from app.services.ai_providers.base import AIToolReply
from app.services.mcp_client import discover_mcp_tools
from app.services.tools.registry import ToolContext, ToolRegistry, ToolResult, tool_registry


AgentEventSink = Callable[[dict[str, Any]], Awaitable[None]]
RegistryFactory = Callable[[], ToolRegistry]
MCPDiscoverer = Callable[[], Awaitable[list[Any]]]


AGENT_RUNTIME_VERSION = "1"


def get_agent_tool_policy_snapshot() -> dict[str, Any]:
    try:
        allowed_tools = sorted(json.loads(settings.AGENT_ALLOWED_TOOLS_JSON))
    except (TypeError, json.JSONDecodeError):
        allowed_tools = []
    try:
        raw_servers = json.loads(settings.MCP_SERVERS_JSON)
    except (TypeError, json.JSONDecodeError):
        raw_servers = []
    mcp_servers = []
    for item in raw_servers if isinstance(raw_servers, list) else []:
        if not isinstance(item, dict) or not item.get("enabled", True):
            continue
        mcp_servers.append({
            "name": str(item.get("name") or "").strip(),
            "allowed_tools": sorted(
                str(name).strip()
                for name in (item.get("allowed_tools") or [])
                if str(name).strip()
            ),
        })
    return {
        "runtime_version": AGENT_RUNTIME_VERSION,
        "allowed_tools": [name for name in allowed_tools if name],
        "mcp_servers": [item for item in mcp_servers if item["name"]],
    }


def get_agent_configuration_version(limits: AgentRuntimeLimits | None = None) -> str:
    limits = limits or AgentRuntimeLimits()
    snapshot = {
        **get_agent_tool_policy_snapshot(),
        "limits": {
            "max_rounds": limits.max_rounds,
            "max_tool_calls_per_round": limits.max_tool_calls_per_round,
            "max_tool_result_chars": limits.max_tool_result_chars,
            "max_history_messages": limits.max_history_messages,
            "tool_timeout_seconds": limits.tool_timeout_seconds,
        },
    }
    digest = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()[:12]
    return f"agent-{AGENT_RUNTIME_VERSION}-{digest}"


@dataclass(frozen=True, slots=True)
class AgentRuntimeLimits:
    max_rounds: int = 3
    max_tool_calls_per_round: int = 4
    max_tool_result_chars: int = 8_000
    max_history_messages: int = 20
    tool_timeout_seconds: float = 30.0


@dataclass(frozen=True, slots=True)
class AgentRuntimeResult:
    run_id: str
    status: str
    text: str
    sources: list[dict]
    input_tokens: int | None
    output_tokens: int | None
    rounds: int
    tool_calls: int


class AgentRuntime:
    """Runs one bounded agent turn independent of HTTP transport."""

    def __init__(
        self,
        *,
        provider: Any,
        limits: AgentRuntimeLimits | None = None,
        registry_factory: RegistryFactory | None = None,
        mcp_discoverer: MCPDiscoverer | None = None,
        event_sink: AgentEventSink | None = None,
    ) -> None:
        self.provider = provider
        self.limits = limits or AgentRuntimeLimits()
        if registry_factory is None:
            self.registry_factory = lambda: tool_registry.scoped(
                set(json.loads(settings.AGENT_ALLOWED_TOOLS_JSON))
            )
        else:
            self.registry_factory = registry_factory
        self.mcp_discoverer = mcp_discoverer or discover_mcp_tools
        self.event_sink = event_sink

        if self.limits.max_rounds <= 0:
            raise ValueError("max_rounds must be positive")
        if self.limits.max_tool_calls_per_round <= 0:
            raise ValueError("max_tool_calls_per_round must be positive")
        if self.limits.max_tool_result_chars <= 0:
            raise ValueError("max_tool_result_chars must be positive")
        if self.limits.max_history_messages <= 0:
            raise ValueError("max_history_messages must be positive")
        if self.limits.tool_timeout_seconds <= 0:
            raise ValueError("tool_timeout_seconds must be positive")

    async def _emit(self, event: dict[str, Any]) -> None:
        if self.event_sink is not None:
            await self.event_sink(event)

    @staticmethod
    def _tool_message_content(result: ToolResult) -> str:
        if result.untrusted:
            return wrap_untrusted_tool_output(
                result.content,
                injection_suspected=result.injection_suspected,
            )
        return result.content

    @staticmethod
    def _history(
        messages: list[dict[str, str]] | None, limit: int
    ) -> list[dict[str, str]]:
        return list(messages or [])[-limit:]

    @staticmethod
    def _assistant_tool_message(reply: AIToolReply) -> dict:
        return {
            "role": "assistant",
            "content": reply.text or None,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments, ensure_ascii=False),
                    },
                }
                for call in reply.tool_calls
            ],
        }

    async def _execute_tool(
        self,
        *,
        registry: ToolRegistry,
        conversation: Conversation,
        current_user: User,
        db: Session,
        name: str,
        arguments: dict[str, Any],
        run_id: str,
        round_number: int,
        call_index: int,
    ) -> ToolResult:
        started_at = time.perf_counter()
        await self._emit(
            {
                "type": "start",
                "run_id": run_id,
                "round": round_number,
                "call_index": call_index,
                "name": name,
            }
        )

        try:
            result = await asyncio.wait_for(
                registry.execute(
                    name,
                    arguments,
                    ToolContext(
                        conversation=conversation,
                        current_user=current_user,
                        db=db,
                    ),
                ),
                timeout=self.limits.tool_timeout_seconds,
            )
        except TimeoutError:
            result = ToolResult(
                content=f"انتهت مهلة تنفيذ الأداة '{name}'.",
                sources=[],
                succeeded=False,
            )
        except asyncio.CancelledError:
            await self._emit(
                {
                    "type": "cancelled",
                    "run_id": run_id,
                    "round": round_number,
                    "call_index": call_index,
                    "name": name,
                }
            )
            raise
        except Exception:
            result = ToolResult(
                content=f"تعذر تنفيذ الأداة '{name}' بسبب خطأ داخلي.",
                sources=[],
                succeeded=False,
            )

        await self._emit(
            {
                "type": "result",
                "run_id": run_id,
                "round": round_number,
                "call_index": call_index,
                "name": name,
                "ok": result.succeeded,
                "duration_ms": int((time.perf_counter() - started_at) * 1000),
            }
        )
        return result

    async def run(
        self,
        *,
        task: str,
        history: list[dict[str, str]],
        conversation: Conversation,
        current_user: User,
        db: Session,
    ) -> AgentRuntimeResult:
        task = task.strip()
        if not task:
            raise ValueError(
                "اكتب المهمة بعد /agent، مثل: /agent ابحث عن أحدث أخبار بايثون."
            )

        run_id = str(uuid.uuid4())
        messages: list[dict] = self._history(
            history, self.limits.max_history_messages
        )
        messages.append({"role": "user", "content": task})

        registry = self.registry_factory()
        for spec in await self.mcp_discoverer():
            if registry.get(spec.name) is None and registry.allows(spec.name):
                registry.register(spec)

        tools = registry.definitions()
        sources: list[dict] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_tool_calls = 0
        rounds_completed = 0
        tool_followups_blocked = False

        await self._emit(
            {
                "type": "runtime_start",
                "run_id": run_id,
                "max_rounds": self.limits.max_rounds,
                "max_tool_calls_per_round": self.limits.max_tool_calls_per_round,
            }
        )

        for round_number in range(1, self.limits.max_rounds + 1):
            rounds_completed = round_number
            await self._emit(
                {
                    "type": "runtime_round_start",
                    "run_id": run_id,
                    "round": round_number,
                }
            )

            available_tools = [] if tool_followups_blocked else tools
            reply = await self.provider.get_reply_with_tools(
                messages,
                available_tools,
                tool_choice="none" if tool_followups_blocked else "auto",
            )
            total_input_tokens += reply.input_tokens or 0
            total_output_tokens += reply.output_tokens or 0

            if not reply.tool_calls:
                final_text = reply.text or "اكتملت المهمة بدون رد نصي."
                await self._emit(
                    {
                        "type": "runtime_complete",
                        "run_id": run_id,
                        "status": "completed",
                        "round": round_number,
                        "tool_calls": total_tool_calls,
                    }
                )
                return AgentRuntimeResult(
                    run_id=run_id,
                    status="completed",
                    text=final_text,
                    sources=sources,
                    input_tokens=total_input_tokens or None,
                    output_tokens=total_output_tokens or None,
                    rounds=rounds_completed,
                    tool_calls=total_tool_calls,
                )

            if tool_followups_blocked:
                final_text = reply.text or (
                    "تم إيقاف استدعاءات الأدوات الإضافية بعد وصول محتوى غير موثوق."
                )
                await self._emit(
                    {
                        "type": "runtime_security_stop",
                        "run_id": run_id,
                        "round": round_number,
                    }
                )
                return AgentRuntimeResult(
                    run_id=run_id,
                    status="stopped",
                    text=final_text,
                    sources=sources,
                    input_tokens=total_input_tokens or None,
                    output_tokens=total_output_tokens or None,
                    rounds=rounds_completed,
                    tool_calls=total_tool_calls,
                )

            calls = reply.tool_calls[: self.limits.max_tool_calls_per_round]
            messages.append(self._assistant_tool_message(reply))

            if len(reply.tool_calls) > len(calls):
                await self._emit(
                    {
                        "type": "runtime_budget",
                        "run_id": run_id,
                        "round": round_number,
                        "dropped_tool_calls": len(reply.tool_calls) - len(calls),
                    }
                )

            for call_index, call in enumerate(calls, start=1):
                total_tool_calls += 1
                result = await self._execute_tool(
                    registry=registry,
                    conversation=conversation,
                    current_user=current_user,
                    db=db,
                    name=call.name,
                    arguments=call.arguments,
                    run_id=run_id,
                    round_number=round_number,
                    call_index=call_index,
                )
                sources.extend(result.sources)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": self._tool_message_content(
                            ToolResult(
                                content=result.content[: self.limits.max_tool_result_chars],
                                sources=result.sources,
                                succeeded=result.succeeded,
                                untrusted=result.untrusted,
                                injection_suspected=result.injection_suspected,
                            )
                        ),
                    }
                )

                if result.untrusted:
                    tool_followups_blocked = True
                    await self._emit(
                        {
                            "type": "runtime_security_block",
                            "run_id": run_id,
                            "round": round_number,
                            "call_index": call_index,
                            "name": call.name,
                            "injection_suspected": result.injection_suspected,
                        }
                    )
                    for skipped_call in calls[call_index:]:
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": skipped_call.id,
                                "name": skipped_call.name,
                                "content": (
                                    "تم حظر استدعاء هذه الأداة بسبب سياسة الأمان: "
                                    "لا تُنفذ استدعاءات أدوات إضافية بعد محتوى غير موثوق."
                                ),
                            }
                        )
                    break

        final_text = (
            "توقّف وضع الوكيل بعد الحد الآمن لعدد خطوات الأدوات. "
            "يمكنك إعادة المحاولة بمهمة أكثر تحديدًا."
        )
        await self._emit(
            {
                "type": "runtime_complete",
                "run_id": run_id,
                "status": "stopped",
                "round": rounds_completed,
                "tool_calls": total_tool_calls,
            }
        )
        return AgentRuntimeResult(
            run_id=run_id,
            status="stopped",
            text=final_text,
            sources=sources,
            input_tokens=total_input_tokens or None,
            output_tokens=total_output_tokens or None,
            rounds=rounds_completed,
            tool_calls=total_tool_calls,
        )
