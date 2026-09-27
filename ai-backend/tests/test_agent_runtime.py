"""Focused tests for the D3 reusable Agent Runtime."""

import asyncio

import pytest

from app.services.agent_runtime import AgentRuntime, AgentRuntimeLimits
from app.services.ai_providers.base import AIToolCall, AIToolReply
from app.services.tools.registry import ToolContext, ToolRegistry, ToolResult, ToolSpec


async def _demo_tool(arguments: dict, context: ToolContext) -> ToolResult:
    del context
    return ToolResult(
        content=f"demo:{arguments.get('value', '')}",
        sources=[{"id": "runtime-test"}],
        succeeded=True,
    )


async def _slow_tool(arguments: dict, context: ToolContext) -> ToolResult:
    del arguments, context
    await asyncio.sleep(0.05)
    return ToolResult(content="late", sources=[], succeeded=True)


def _registry(handler) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="demo",
            description="test tool",
            parameters={
                "type": "object",
                "properties": {"value": {"type": "string"}},
            },
            handler=handler,
        )
    )
    return registry


class TwoStepProvider:
    def __init__(self):
        self.calls = 0
        self.messages_seen = []

    async def get_reply_with_tools(self, messages, tools, tool_choice="auto"):
        self.calls += 1
        self.messages_seen.append(messages)
        assert tool_choice == "auto"
        assert tools[0]["function"]["name"] == "demo"
        if self.calls == 1:
            return AIToolReply(
                tool_calls=[
                    AIToolCall(
                        id="call-1",
                        name="demo",
                        arguments={"value": "ok"},
                    )
                ]
            )
        return AIToolReply(text="done")


async def _empty_discovery():
    return []


def test_runtime_completes_with_tool_and_lifecycle_events():
    provider = TwoStepProvider()
    events = []

    async def emit(event):
        events.append(event)

    runtime = AgentRuntime(
        provider=provider,
        registry_factory=lambda: _registry(_demo_tool),
        mcp_discoverer=_empty_discovery,
        event_sink=emit,
    )

    result = asyncio.run(
        runtime.run(
            task="run demo",
            history=[{"role": "user", "content": str(i)} for i in range(25)],
            conversation=object(),
            current_user=object(),
            db=object(),
        )
    )

    assert result.status == "completed"
    assert result.text == "done"
    assert result.rounds == 2
    assert result.tool_calls == 1
    assert result.sources == [{"id": "runtime-test"}]
    assert result.run_id

    event_types = [event["type"] for event in events]
    assert event_types[0] == "runtime_start"
    assert "runtime_round_start" in event_types
    assert "start" in event_types
    assert "result" in event_types
    assert event_types[-1] == "runtime_complete"
    assert {event["run_id"] for event in events} == {result.run_id}

    first_messages = provider.messages_seen[0]
    assert len(first_messages) == 21


def test_runtime_times_out_tool_without_aborting_the_run():
    provider = TwoStepProvider()
    runtime = AgentRuntime(
        provider=provider,
        limits=AgentRuntimeLimits(tool_timeout_seconds=0.01),
        registry_factory=lambda: _registry(_slow_tool),
        mcp_discoverer=_empty_discovery,
    )

    result = asyncio.run(
        runtime.run(
            task="run slow tool",
            history=[],
            conversation=object(),
            current_user=object(),
            db=object(),
        )
    )

    assert result.status == "completed"
    assert result.text == "done"
    assert provider.calls == 2


def test_runtime_rejects_invalid_limits():
    with pytest.raises(ValueError, match="max_rounds"):
        AgentRuntime(
            provider=object(),
            limits=AgentRuntimeLimits(max_rounds=0),
        )
