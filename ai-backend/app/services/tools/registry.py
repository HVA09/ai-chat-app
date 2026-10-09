"""Central registry for safe agent tools.

D1 establishes one source of truth for:
- tool metadata exposed to the model
- tool lookup/dispatch
- bounded execution context
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import difflib
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
from app.models.project_file import ProjectFile
from app.models.user import User
from app.schemas.project_files import ProjectFileCreate
from app.services.tools.calculator import CalculatorError, calculate_expression
from app.services.tools.code_execution import CodeExecutionError, execute_python_code
from app.services.tools.data_analysis import DataAnalysisError, DataFile, analyze_file
from app.services.storage import delete_file as delete_stored_file, materialize_file, put_file
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


def _get_attached_data_attachment(
    conversation: Conversation,
    current_user: User,
    filename: str,
    db: Session,
) -> FileAttachment:
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

    return attachment


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
        attachment = _get_attached_data_attachment(
            context.conversation,
            context.current_user,
            filename,
            context.db,
        )
        fallback_path = (
            Path(settings.UPLOAD_DIR)
            / str(context.current_user.id)
            / attachment.stored_filename
        )
        with materialize_file(attachment.object_key, fallback_path) as path:
            data_file = DataFile(
                path=path,
                original_filename=attachment.original_filename,
                content_type=attachment.content_type,
            )
            result = analyze_file(data_file)
        source = {
            "id": "D1",
            "filename": attachment.original_filename,
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

        project_id = context.conversation.project_id
        project_file_count = 0
        if project_id is not None:
            existing_project_files = (
                context.db.query(ProjectFile)
                .filter(ProjectFile.project_id == project_id)
                .all()
            )
            existing_by_path = {item.path: item for item in existing_project_files}
            new_paths = [path for path, _ in normalized_files if path not in existing_by_path]
            if len(existing_project_files) + len(new_paths) > 200:
                raise ValueError("المشروع تجاوز الحد الأقصى 200 ملف مصدر.")

            for path, content in normalized_files:
                project_file = existing_by_path.get(path)
                if project_file is None:
                    project_file = ProjectFile(
                        project_id=project_id,
                        path=path,
                        content=content,
                    )
                    context.db.add(project_file)
                else:
                    project_file.content = content
                project_file_count += 1

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

    project_suffix = (
        f" وتم تحديث {project_file_count} ملفًا في شجرة المشروع."
        if context.conversation.project_id is not None
        else ""
    )
    return ToolResult(
        content=f"تم إنشاء حزمة المشروع «{original_filename}» ويمكن تنزيلها من قسم الملفات أو من المصادر أسفل الرد.{project_suffix}",
        sources=[{
            "id": "P1",
            "filename": original_filename,
            "file_id": attachment.id,
            "kind": "project-artifact",
        }],
        succeeded=True,
    )

def _current_project_id(context: ToolContext) -> int | None:
    project_id = context.conversation.project_id
    return int(project_id) if project_id is not None else None


def _validated_project_path(raw_path: Any) -> str:
    return ProjectFileCreate(path=str(raw_path or ""), content="").path


async def _list_project_files(arguments: dict[str, Any], context: ToolContext) -> ToolResult:
    del arguments
    project_id = _current_project_id(context)
    if project_id is None:
        return ToolResult(
            content="لا يمكن استكشاف ملفات المشروع لأن المحادثة الحالية غير مرتبطة بمشروع.",
            sources=[],
            succeeded=False,
        )

    files = (
        context.db.query(ProjectFile)
        .filter(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.path.asc(), ProjectFile.id.asc())
        .limit(200)
        .all()
    )
    if not files:
        return ToolResult(
            content="المشروع لا يحتوي على ملفات مصدر بعد.",
            sources=[],
            succeeded=True,
        )

    lines = [
        f"- {item.path} ({len(item.content)} حرف)"
        for item in files
    ]
    return ToolResult(
        content=f"ملفات المشروع ({len(files)}):\n" + "\n".join(lines),
        sources=[],
        succeeded=True,
        untrusted=True,
    )


async def _read_project_file(arguments: dict[str, Any], context: ToolContext) -> ToolResult:
    project_id = _current_project_id(context)
    if project_id is None:
        return ToolResult(
            content="لا يمكن قراءة ملف مشروع لأن المحادثة الحالية غير مرتبطة بمشروع.",
            sources=[],
            succeeded=False,
        )

    try:
        path = _validated_project_path(arguments.get("path"))
        max_chars = max(1000, min(int(arguments.get("max_chars") or 20_000), 20_000))
    except (TypeError, ValueError) as exc:
        return ToolResult(
            content=f"مسار أو حد قراءة غير صالح: {exc}",
            sources=[],
            succeeded=False,
        )

    project_file = (
        context.db.query(ProjectFile)
        .filter(
            ProjectFile.project_id == project_id,
            ProjectFile.path == path,
        )
        .first()
    )
    if project_file is None:
        return ToolResult(
            content=f"لم أجد ملف المشروع: {path}",
            sources=[],
            succeeded=False,
        )

    content = project_file.content
    truncated = len(content) > max_chars
    body = content[:max_chars]
    suffix = "\n... تم اختصار الملف ضمن حد القراءة الآمن." if truncated else ""
    return ToolResult(
        content=f"ملف: {path}\n\n{body}{suffix}",
        sources=[{
            "id": f"project-file:{project_file.id}",
            "project_id": project_id,
            "file_id": project_file.id,
            "filename": path,
            "kind": "project-file",
        }],
        succeeded=True,
        untrusted=True,
    )


async def _search_project_files(arguments: dict[str, Any], context: ToolContext) -> ToolResult:
    project_id = _current_project_id(context)
    if project_id is None:
        return ToolResult(
            content="لا يمكن البحث داخل ملفات المشروع لأن المحادثة الحالية غير مرتبطة بمشروع.",
            sources=[],
            succeeded=False,
        )

    query = str(arguments.get("query") or "").strip()
    if not query:
        return ToolResult(
            content="اذكر نص البحث داخل ملفات المشروع.",
            sources=[],
            succeeded=False,
        )
    max_results = max(1, min(int(arguments.get("max_results") or 20), 20))
    needle = query.casefold()
    files = (
        context.db.query(ProjectFile)
        .filter(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.path.asc(), ProjectFile.id.asc())
        .limit(200)
        .all()
    )

    matches: list[str] = []
    for item in files:
        for line_number, line in enumerate(item.content.splitlines(), start=1):
            if needle not in line.casefold():
                continue
            snippet = line.strip()
            if len(snippet) > 500:
                snippet = snippet[:500] + "…"
            matches.append(f"{item.path}:{line_number}: {snippet}")
            if len(matches) >= max_results:
                break
        if len(matches) >= max_results:
            break

    if not matches:
        return ToolResult(
            content=f"لم أجد «{query}» داخل ملفات المشروع.",
            sources=[],
            succeeded=True,
            untrusted=True,
        )

    return ToolResult(
        content=f"نتائج البحث عن «{query}»:\n" + "\n".join(matches),
        sources=[],
        succeeded=True,
        untrusted=True,
    )


async def _edit_project_file(arguments: dict[str, Any], context: ToolContext) -> ToolResult:
    """Safely create or update one source file inside the current project."""
    project_id = context.conversation.project_id
    if project_id is None:
        return ToolResult(
            content="لا يمكن تعديل ملف مشروع لأن المحادثة الحالية غير مرتبطة بمشروع.",
            sources=[],
            succeeded=False,
        )

    try:
        payload = ProjectFileCreate(
            path=str(arguments.get("path") or ""),
            content=str(arguments.get("content") or ""),
        )
    except Exception as exc:
        return ToolResult(
            content=f"تم رفض تعديل ملف المشروع: {exc}",
            sources=[],
            succeeded=False,
        )

    expected_content = arguments.get("expected_content")
    if expected_content is not None and not isinstance(expected_content, str):
        return ToolResult(
            content="expected_content يجب أن يكون نصًا عندما يتم تمريره.",
            sources=[],
            succeeded=False,
        )

    project_file = (
        context.db.query(ProjectFile)
        .filter(
            ProjectFile.project_id == project_id,
            ProjectFile.path == payload.path,
        )
        .first()
    )

    if expected_content is not None:
        current = project_file.content if project_file is not None else ""
        if current != expected_content:
            return ToolResult(
                content=(f"لم يتم تعديل {payload.path}: الملف تغيّر منذ آخر قراءة. "
                         "أعد قراءة الملف قبل محاولة التعديل مرة أخرى."),
                sources=[],
                succeeded=False,
            )

    if project_file is None:
        count = (
            context.db.query(func.count(ProjectFile.id))
            .filter(ProjectFile.project_id == project_id)
            .scalar()
            or 0
        )
        if count >= 200:
            return ToolResult(
                content="لا يمكن إنشاء ملف جديد: وصل المشروع إلى الحد الأقصى 200 ملف مصدر.",
                sources=[],
                succeeded=False,
            )
        project_file = ProjectFile(
            project_id=project_id,
            path=payload.path,
            content=payload.content,
        )
        old_content = ""
    else:
        old_content = project_file.content
        if old_content == payload.content:
            return ToolResult(
                content=f"لم يتغير محتوى {payload.path}.",
                sources=[{
                    "id": f"project-file:{project_file.id}",
                    "project_id": project_id,
                    "file_id": project_file.id,
                    "filename": payload.path,
                    "kind": "project-file",
                }],
                succeeded=True,
            )
        project_file.content = payload.content

    diff = "\n".join(
        difflib.unified_diff(
            old_content.splitlines(),
            payload.content.splitlines(),
            fromfile=f"a/{payload.path}",
            tofile=f"b/{payload.path}",
            lineterm="",
            n=3,
        )
    )
    try:
        if project_file.id is None:
            context.db.add(project_file)
        context.db.commit()
        context.db.refresh(project_file)
    except Exception as exc:
        context.db.rollback()
        return ToolResult(
            content=f"تعذر حفظ تعديل {payload.path}: {exc}",
            sources=[],
            succeeded=False,
        )

    diff_preview = diff[:6000]
    if len(diff) > 6000:
        diff_preview += "\n... تم اختصار الـdiff لحد العرض الآمن."

    return ToolResult(
        content=f"تم تعديل ملف المشروع {payload.path}.\n\nDiff:\n{diff_preview}",
        sources=[{
            "id": f"project-file:{project_file.id}",
            "project_id": project_id,
            "file_id": project_file.id,
            "filename": payload.path,
            "kind": "project-file",
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
        description="Build a downloadable ZIP project from small text files. When the user asks to build or create a project, use this tool instead of claiming the agent is text-only. Never execute the generated code.",
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

tool_registry.register(
    ToolSpec(
        name="list_project_files",
        description=(
            "List the source files in the project attached to the current conversation. "
            "Returns paths and bounded metadata only; never executes project code."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        handler=_list_project_files,
        output_trust="untrusted",
    )
)

tool_registry.register(
    ToolSpec(
        name="read_project_file",
        description=(
            "Read one text source file from the project attached to the current conversation. "
            "Use before editing so expected_content can protect against stale writes. Never execute project code."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative source path."},
                "max_chars": {
                    "type": "integer",
                    "minimum": 1000,
                    "maximum": 20000,
                    "description": "Maximum characters to return.",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        handler=_read_project_file,
        output_trust="untrusted",
    )
)

tool_registry.register(
    ToolSpec(
        name="search_project_files",
        description=(
            "Search text inside the source files of the current project. "
            "Use it to locate relevant code before editing. Never execute project code."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1, "maxLength": 500},
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        handler=_search_project_files,
        output_trust="untrusted",
    )
)

tool_registry.register(
    ToolSpec(
        name="edit_project_file",
        description=(
            "Create or update one text source file inside the project attached to the current conversation. "
            "Use expected_content for safe optimistic concurrency. Returns a bounded unified diff. "
            "Never execute project code."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project-relative source path."},
                "content": {"type": "string", "description": "Complete replacement text for the file."},
                "expected_content": {
                    "type": "string",
                    "description": "Optional exact previous content. Prevents overwriting a newer edit.",
                },
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
        handler=_edit_project_file,
        output_trust="untrusted",
    )
)
