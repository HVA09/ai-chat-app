"""Central registry for safe agent tools.

D1 establishes one source of truth for:
- tool metadata exposed to the model
- tool lookup/dispatch
- bounded execution context
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import uuid
import zipfile
from typing import Any, Awaitable, Callable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.conversation import Conversation
from app.models.conversation_file_link import ConversationFileLink
from app.models.file_attachment import FileAttachment
from app.models.user import User
from app.services.tools.calculator import CalculatorError, calculate_expression
from app.services.tools.code_execution import CodeExecutionError, execute_python_code
from app.services.tools.data_analysis import DataAnalysisError, DataFile, analyze_file
from app.services.storage import put_file, delete_file as delete_stored_file
from app.services.tool_security import (
    ToolArgumentSecurityError,
    inspect_untrusted_output,
    validate_tool_arguments,
)
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
    untrusted: bool = False
    injection_suspected: bool = False


ToolHandler = Callable[[dict[str, Any], ToolContext], Awaitable[ToolResult]]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler
    output_trust: str = "trusted"

    def as_provider_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolPermissionError(PermissionError):
    """Raised when a tool is outside the registry's explicit allowlist."""


class ToolRegistry:
    """Central registry used by agent mode for discovery and execution."""

    def __init__(self, allowed_names: set[str] | None = None) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._allowed_names = (
            None if allowed_names is None else frozenset(allowed_names)
        )

    def register(self, spec: ToolSpec) -> None:
        if self._allowed_names is not None and spec.name not in self._allowed_names:
            raise ToolPermissionError(f"Tool is not permitted: {spec.name}")
        if spec.name in self._tools:
            raise ValueError(f"Tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    def scoped(self, allowed_names: set[str] | None = None) -> "ToolRegistry":
        effective_allowed = (
            self._allowed_names if allowed_names is None else frozenset(allowed_names)
        )
        scoped = ToolRegistry(
            None if effective_allowed is None else set(effective_allowed)
        )
        if effective_allowed is None:
            scoped._tools = self._tools.copy()
        else:
            scoped._tools = {
                name: spec
                for name, spec in self._tools.items()
                if name in effective_allowed
            }
        return scoped

    def allows(self, name: str) -> bool:
        return self._allowed_names is None or name in self._allowed_names

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
            validate_tool_arguments(
                spec.parameters,
                arguments,
                max_chars=settings.AGENT_MAX_TOOL_ARGUMENT_CHARS,
                max_depth=settings.AGENT_MAX_TOOL_ARGUMENT_DEPTH,
            )
        except ToolArgumentSecurityError as exc:
            return ToolResult(
                content=f"تم رفض مدخلات الأداة '{name}' لأسباب أمنية: {exc}",
                sources=[],
                succeeded=False,
            )

        result = await spec.handler(arguments, context)
        if spec.output_trust == "untrusted":
            security = inspect_untrusted_output(result.content)
            return ToolResult(
                content=result.content,
                sources=result.sources,
                succeeded=result.succeeded,
                untrusted=True,
                injection_suspected=security.injection_suspected,
            )
        return result


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



async def _create_project_archive(arguments: dict[str, Any], context: ToolContext) -> ToolResult:
    """Create a safe, text-only project ZIP and expose it through the existing files API."""
    project_name = str(arguments.get("project_name") or "ai-project").strip()
    files = arguments.get("files")
    if not project_name or not isinstance(files, list) or not files:
        return ToolResult(
            content="لإنشاء مشروع، أرسل اسم المشروع وقائمة ملفات تحتوي على المسار والمحتوى.",
            sources=[],
            succeeded=False,
        )

    if len(files) > 50:
        return ToolResult(content="المشروع أكبر من الحد الآمن: الحد الأقصى 50 ملفًا.", sources=[], succeeded=False)

    safe_project_name = re.sub(r"[^A-Za-z0-9._-]+", "-", project_name).strip("-._")[:80] or "ai-project"
    seen_paths: set[str] = set()
    normalized_files: list[tuple[str, str]] = []
    total_chars = 0

    for item in files:
        if not isinstance(item, dict):
            return ToolResult(content="كل ملف يجب أن يكون كائنًا يحتوي على path وcontent.", sources=[], succeeded=False)
        raw_path = str(item.get("path") or "").replace("\\", "/").strip()
        content = item.get("content")
        if not raw_path or not isinstance(content, str):
            return ToolResult(content="ملف غير صالح: يجب أن يكون path نصًا وcontent نصًا.", sources=[], succeeded=False)
        path_obj = Path(raw_path)
        if path_obj.is_absolute() or ".." in path_obj.parts or raw_path.startswith("/"):
            return ToolResult(content=f"مسار ملف غير آمن: {raw_path}", sources=[], succeeded=False)
        normalized = "/".join(part for part in path_obj.parts if part not in {"", "."})
        if not normalized:
            return ToolResult(content="يوجد ملف بلا مسار صالح.", sources=[], succeeded=False)
        if normalized in seen_paths:
            return ToolResult(content=f"المسار مكرر: {normalized}", sources=[], succeeded=False)
        if len(content) > 50_000:
            return ToolResult(content=f"الملف كبير جدًا: {normalized}", sources=[], succeeded=False)
        total_chars += len(content)
        if total_chars > 450_000:
            return ToolResult(content="حجم محتوى المشروع أكبر من الحد الآمن 450 ألف حرف.", sources=[], succeeded=False)
        seen_paths.add(normalized)
        normalized_files.append((normalized, content))

    user_dir = Path(settings.UPLOAD_DIR) / str(context.current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid.uuid4().hex}.zip"
    destination = user_dir / stored_filename
    object_key = f"users/{context.current_user.id}/{stored_filename}"
    original_filename = f"{safe_project_name}.zip"

    try:
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path, content in normalized_files:
                archive.writestr(path, content)
        size_bytes = destination.stat().st_size

        current_files = (
            context.db.query(func.count(FileAttachment.id))
            .filter(FileAttachment.user_id == context.current_user.id)
            .scalar()
            or 0
        )
        current_storage = (
            context.db.query(func.coalesce(func.sum(FileAttachment.size_bytes), 0))
            .filter(FileAttachment.user_id == context.current_user.id)
            .scalar()
            or 0
        )
        if current_files >= settings.MAX_FILES_PER_USER:
            destination.unlink(missing_ok=True)
            return ToolResult(content="وصلت إلى الحد الأقصى لعدد الملفات في الحساب.", sources=[], succeeded=False)
        if current_storage + size_bytes > settings.MAX_STORAGE_PER_USER_MB * 1024 * 1024:
            destination.unlink(missing_ok=True)
            return ToolResult(content="مساحة التخزين في الحساب لا تكفي لحفظ حزمة المشروع.", sources=[], succeeded=False)

        try:
            put_file(destination, object_key, "application/zip")
        except Exception:
            destination.unlink(missing_ok=True)
            raise

        attachment = FileAttachment(
            user_id=context.current_user.id,
            workspace_id=context.conversation.workspace_id,
            project_id=context.conversation.project_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            object_key=object_key,
            content_type="application/zip",
            size_bytes=size_bytes,
            extracted_text=None,
        )
        context.db.add(attachment)
        context.db.flush()
        context.db.add(
            ConversationFileLink(
                conversation_id=context.conversation.id,
                file_id=attachment.id,
            )
        )
        context.db.commit()
        context.db.refresh(attachment)
    except Exception as exc:
        context.db.rollback()
        try:
            if destination.exists():
                destination.unlink(missing_ok=True)
            delete_stored_file(object_key, destination)
        except Exception:
            pass
        return ToolResult(
            content=f"تعذر إنشاء حزمة المشروع: {exc}",
            sources=[],
            succeeded=False,
        )

    return ToolResult(
        content=f"تم إنشاء حزمة المشروع «{original_filename}» ويمكن تنزيلها من قسم الملفات أو من المصادر أسفل الرد.",
        sources=[{
            "id": "P1",
            "filename": original_filename,
            "file_id": attachment.id,
            "kind": "project-artifact",
        }],
        succeeded=True,
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
        output_trust="untrusted",
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
        output_trust="untrusted",
    )
)

tool_registry.register(
    ToolSpec(
        name="create_project_archive",
        description="Create a downloadable ZIP project from small text files. Use for building a project from scratch. Never execute the generated code.",
        parameters={
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "description": "Short project name."},
                "files": {
                    "type": "array",
                    "description": "Project text files. Each item contains path and content.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                        "additionalProperties": False,
                    },
                    "maxItems": 50,
                },
            },
            "required": ["project_name", "files"],
            "additionalProperties": False,
        },
        handler=_create_project_archive,
    )
)
