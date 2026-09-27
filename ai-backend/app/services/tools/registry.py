"""Central registry for safe agent tools.

D1 establishes one source of truth for:
- tool metadata exposed to the model
- tool lookup/dispatch
- bounded execution context
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from sqlalchemy.orm import Session

from app.config import settings
from app.models.conversation import Conversation
from app.models.conversation_file_link import ConversationFileLink
from app.models.file_attachment import FileAttachment
from app.models.user import User
from app.services.tools.calculator import CalculatorError, calculate_expression
from app.services.tools.code_execution import CodeExecutionError, execute_python_code
from app.services.tools.data_analysis import DataAnalysisError, DataFile, analyze_file
from app.services.tools.web_search import (
    WebSearchError,
    format_web_search_response,
    search_web,
)


@dataclass(frozen=True, slots=True)
class ToolContext:
    conversation: Conversation
    current_user: User
    db: Session


@dataclass(frozen=True, slots=True)
class ToolResult:
    content: str
    sources: list[dict]
    succeeded: bool


ToolHandler = Callable[[dict[str, Any], ToolContext], Awaitable[ToolResult]]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler

    def as_provider_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Central registry used by agent mode for discovery and execution."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    def definitions(self) -> list[dict]:
        return [tool.as_provider_definition() for tool in self._tools.values()]

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        spec = self.get(name)
        if spec is None:
            return ToolResult(
                content=f"الأداة '{name}' غير متاحة.",
                sources=[],
                succeeded=False,
            )

        try:
            return await spec.handler(arguments, context)
        except Exception:
            return ToolResult(
                content=f"تعذر تنفيذ الأداة '{name}'.",
                sources=[],
                succeeded=False,
            )


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


async def _calculator(arguments: dict[str, Any], context: ToolContext) -> ToolResult:
    del context
    expression = str(arguments.get("expression") or "").strip()
    try:
        return ToolResult(
            content=calculate_expression(expression),
            sources=[],
            succeeded=True,
        )
    except CalculatorError as exc:
        return ToolResult(
            content=f"تعذر تنفيذ الحساب: {exc}",
            sources=[],
            succeeded=False,
        )


async def _python(arguments: dict[str, Any], context: ToolContext) -> ToolResult:
    del context
    code = str(arguments.get("code") or "")
    try:
        return ToolResult(
            content=execute_python_code(code),
            sources=[],
            succeeded=True,
        )
    except CodeExecutionError as exc:
        return ToolResult(
            content=f"تعذر تنفيذ كود بايثون: {exc}",
            sources=[],
            succeeded=False,
        )


async def _web_search(arguments: dict[str, Any], context: ToolContext) -> ToolResult:
    del context
    query = str(arguments.get("query") or "").strip()
    try:
        results = await search_web(query)
        reply, sources = format_web_search_response(query, results)
        return ToolResult(content=reply, sources=sources, succeeded=True)
    except WebSearchError as exc:
        return ToolResult(
            content=f"تعذر تنفيذ بحث الويب: {exc}",
            sources=[],
            succeeded=False,
        )


async def _analyze_data(arguments: dict[str, Any], context: ToolContext) -> ToolResult:
    filename = str(arguments.get("filename") or "").strip()
    try:
        data_file = _get_attached_data_file(
            context.conversation,
            context.current_user,
            filename,
            context.db,
        )
        result = analyze_file(data_file)
        source = {
            "id": "D1",
            "filename": data_file.original_filename,
            "chunk": None,
            "kind": "data-analysis",
        }
        return ToolResult(content=result, sources=[source], succeeded=True)
    except DataAnalysisError as exc:
        return ToolResult(
            content=f"تعذر تحليل ملف البيانات: {exc}",
            sources=[],
            succeeded=False,
        )


tool_registry = ToolRegistry()

tool_registry.register(
    ToolSpec(
        name="calculator",
        description="Safely calculate a mathematical expression. Use for arithmetic only.",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A mathematical expression using numbers and + - * / // % ** and parentheses.",
                }
            },
            "required": ["expression"],
        },
        handler=_calculator,
    )
)
tool_registry.register(
    ToolSpec(
        name="python",
        description="Execute a small, safe Python program for calculations or data transformation. No imports, filesystem, network, or arbitrary builtins are available.",
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code using basic variables, loops, lists/dicts, print(), math/statistics helper functions, and simple expressions.",
                }
            },
            "required": ["code"],
        },
        handler=_python,
    )
)
tool_registry.register(
    ToolSpec(
        name="web_search",
        description="Search the public web for current information. Use when the user explicitly needs web/current information.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A concise web search query.",
                }
            },
            "required": ["query"],
        },
        handler=_web_search,
    )
)
tool_registry.register(
    ToolSpec(
        name="analyze_data",
        description="Analyze a CSV or XLSX file attached to the current conversation.",
        parameters={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The exact or partial original filename of an attached CSV/XLSX file.",
                }
            },
            "required": ["filename"],
        },
        handler=_analyze_data,
    )
)
