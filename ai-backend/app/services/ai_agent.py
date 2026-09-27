"""Agent mode: model-driven selection of safe built-in tools."""

from __future__ import annotations

from typing import Awaitable, Callable

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.user import User
from app.services.agent_runtime import AgentRuntime
from app.services.ai_providers.factory import get_provider
from app.services.ai_providers.openai_provider import OpenAICompatibleProvider


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

    try:
        result = await AgentRuntime(
            provider=provider,
            event_sink=on_tool_event,
        ).run(
            task=task,
            history=history,
            conversation=conversation,
            current_user=current_user,
            db=db,
        )
    except ValueError as exc:
        raise AgentModeError(str(exc)) from exc

    return (
        result.text,
        result.sources,
        result.input_tokens,
        result.output_tokens,
    )
