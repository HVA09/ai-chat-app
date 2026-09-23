"""Agent mode: model-driven selection of safe built-in tools.

The agent only exposes local, bounded tools already present in the app.
It never executes arbitrary Python/code supplied by the user.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Awaitable, Callable

from sqlalchemy.orm import Session

from app.config import settings
from app.models.conversation import Conversation
from app.models.conversation_file_link import ConversationFileLink
from app.models.file_attachment import FileAttachment
from app.models.user import User
from app.services.ai_providers.base import AIToolReply
from app.services.ai_providers.factory import get_provider
from app.services.ai_providers.openai_provider import OpenAICompatibleProvider
from app.services.tools.calculator import CalculatorError, calculate_expression
from app.services.tools.code_execution import CodeExecutionError, execute_python_code
from app.services.tools.data_analysis import DataAnalysisError, DataFile, analyze_file
from app.services.tools.web_search import WebSearchError, format_web_search_response, search_web

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


def _tool_definitions() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": "Safely calculate a mathematical expression. Use for arithmetic only.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "A mathematical expression using numbers and + - * / // % ** and parentheses.",
                        }
                    },
                    "required": ["expression"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "python",
                "description": "Execute a small, safe Python program for calculations or data transformation. No imports, filesystem, network, or arbitrary builtins are available.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code using basic variables, loops, lists/dicts, print(), math/statistics helper functions, and simple expressions."
                        }
                    },
                    "required": ["code"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the public web for current information. Use when the user explicitly needs web/current information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "A concise web search query.",
                        }
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_data",
                "description": "Analyze a CSV or XLSX file attached to the current conversation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "The exact or partial original filename of an attached CSV/XLSX file.",
                        }
                    },
                    "required": ["filename"],
                },
            },
        },
    ]


def _history(messages: list[dict[str, str]] | None) -> list[dict[str, str]]:
    return list(messages or [])[-MAX_AGENT_HISTORY:]


def _get_attached_data_file(
    conversation: Conversation,
    current_user: User,
    filename: str,
    db: Session,
) -> DataFile:
    requested = filename.strip().casefold()
    if not requested:
        raise DataAnalysisError("اذكر اسم ملف CSV/XLSX المرفق الذي تريد تحليله.")

    attachments = (
        db.query(FileAttachment)
        .join(ConversationFileLink, ConversationFileLink.file_id == FileAttachment.id)
        .filter(
            ConversationFileLink.conversation_id == conversation.id,
            FileAttachment.user_id == current_user.id,
        )
        .order_by(ConversationFileLink.created_at.asc())
        .all()
    )

    attachment = next(
        (item for item in attachments if item.original_filename.casefold() == requested),
        None,
    ) or next(
        (item for item in attachments if requested in item.original_filename.casefold()),
        None,
    )
    if attachment is None:
        names = ", ".join(item.original_filename for item in attachments[:8])
        suffix = f" الملفات المرفقة: {names}." if names else " لا توجد ملفات مرفقة."
        raise DataAnalysisError(f"لم أجد ملف البيانات المطلوب.{suffix}")

    path = Path(settings.UPLOAD_DIR) / str(current_user.id) / attachment.stored_filename
    if not path.exists():
        raise DataAnalysisError("الملف المطلوب غير موجود على القرص.")

    return DataFile(
        path=path,
        original_filename=attachment.original_filename,
        content_type=attachment.content_type,
    )


async def _execute_tool(
    name: str,
    arguments: dict,
    conversation: Conversation,
    current_user: User,
    db: Session,
) -> tuple[str, list[dict], bool]:
    if name == "calculator":
        expression = str(arguments.get("expression") or "").strip()
        try:
            return calculate_expression(expression), [], True
        except CalculatorError as exc:
            return f"تعذر تنفيذ الحساب: {exc}", [], False

    if name == "python":
        code = str(arguments.get("code") or "")
        try:
            return execute_python_code(code), [], True
        except CodeExecutionError as exc:
            return f"تعذر تنفيذ كود بايثون: {exc}", [], False

    if name == "web_search":
        query = str(arguments.get("query") or "").strip()
        try:
            results = await search_web(query)
            reply, sources = format_web_search_response(query, results)
            return reply, sources, True
        except WebSearchError as exc:
            return f"تعذر تنفيذ بحث الويب: {exc}", [], False

    if name == "analyze_data":
        filename = str(arguments.get("filename") or "").strip()
        try:
            data_file = _get_attached_data_file(conversation, current_user, filename, db)
            result = analyze_file(data_file)
            source = {
                "id": "D1",
                "filename": data_file.original_filename,
                "chunk": None,
                "kind": "data-analysis",
            }
            return result, [source], True
        except DataAnalysisError as exc:
            return f"تعذر تحليل ملف البيانات: {exc}", [], False

    return f"الأداة '{name}' غير متاحة.", [], False


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
    tools = _tool_definitions()
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

            result, call_sources, succeeded = await _execute_tool(
                call.name, call.arguments, conversation, current_user, db
            )
            sources.extend(call_sources)

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
                    "content": result[:MAX_TOOL_RESULT_CHARS],
                }
            )

    return (
        "توقّف وضع الوكيل بعد الحد الآمن لعدد خطوات الأدوات. "
        "يمكنك إعادة المحاولة بمهمة أكثر تحديدًا.",
        sources,
        total_input_tokens or None,
        total_output_tokens or None,
    )
