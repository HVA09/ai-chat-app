"""Agent mode: model-driven selection of safe built-in tools.

The agent only exposes local, bounded tools already present in the app.
It never executes arbitrary Python/code supplied by the user.
"""
from __future__ import annotations

import json
import time
from typing import Awaitable, Callable

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.user import User
from app.services.ai_providers.base import AIToolReply
from app.services.ai_providers.factory import get_provider
from app.services.ai_providers.openai_provider import OpenAICompatibleProvider
from app.services.tools.registry import ToolContext, tool_registry

MAX_AGENT_ROUNDS = 3
MAX_TOOL_CALLS_PER_ROUND = 4
MAX_TOOL_RESULT_CHARS = 8_000
MAX_AGENT_HISTORY = 20


class AgentModeError(ValueError):
    """User-facing error for agent-mode limitations."""


def extract_agent_request(message: str) -> str | None:
    text = message.strip()
    for prefix in ("/agent", "/run"):
        if text == prefix:
            return ""
        if text.startswith(prefix + " "):
            return text[len(prefix) + 1 :].strip()
    return None


def _history(messages: list[dict[str, str]] | None) -> list[dict[str, str]]:
    return list(messages or [])[-MAX_AGENT_HISTORY:]


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


async def run_agent(
    task: str,
    history: list[dict[str, str]],
    conversation: Conversation,
    current_user: User,
    db: Session,
    model: str | None = None,
    on_tool_event: Callable[[dict], Awaitable[None]] | None = None,
) -> tuple[str, list[dict], int | None, int | None]:
    provider = get_provider(model)
    if not isinstance(provider, OpenAICompatibleProvider):
        raise AgentModeError(
            "وضع الوكيل متاح حاليًا مع المزوّدات المتوافقة مع OpenAI فقط."
        )

    task = task.strip()
    if not task:
        raise AgentModeError("اكتب المهمة بعد /agent، مثل: /agent ابحث عن أحدث أخبار بايثون.")

    messages: list[dict] = _history(history) + [{"role": "user", "content": task}]
    tools = tool_registry.definitions()
    sources: list[dict] = []
    total_input_tokens = 0
    total_output_tokens = 0

    for _ in range(MAX_AGENT_ROUNDS):
        reply = await provider.get_reply_with_tools(messages, tools, tool_choice="auto")
        total_input_tokens += reply.input_tokens or 0
        total_output_tokens += reply.output_tokens or 0

        if not reply.tool_calls:
            return (
                reply.text or "اكتملت المهمة بدون رد نصي.",
                sources,
                total_input_tokens or None,
                total_output_tokens or None,
            )

        calls = reply.tool_calls[:MAX_TOOL_CALLS_PER_ROUND]
        messages.append(_assistant_tool_message(reply))

        for call in calls:
            started_at = time.perf_counter()
            if on_tool_event is not None:
                await on_tool_event({
                    "type": "start",
                    "name": call.name,
                })

            result = await tool_registry.execute(
                call.name,
                call.arguments,
                ToolContext(
                    conversation=conversation,
                    current_user=current_user,
                    db=db,
                ),
            )
            sources.extend(result.sources)
            succeeded = result.succeeded

            if on_tool_event is not None:
                await on_tool_event({
                    "type": "result",
                    "name": call.name,
                    "ok": succeeded,
                    "duration_ms": int((time.perf_counter() - started_at) * 1000),
                })

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.name,
                    "content": result.content[:MAX_TOOL_RESULT_CHARS],
                }
            )

    return (
        "توقّف وضع الوكيل بعد الحد الآمن لعدد خطوات الأدوات. "
        "يمكنك إعادة المحاولة بمهمة أكثر تحديدًا.",
        sources,
        total_input_tokens or None,
        total_output_tokens or None,
    )

