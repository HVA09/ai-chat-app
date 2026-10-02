"""مسارات المشاريع داخل مساحات العمل."""
import json
import re
import tomllib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.assistant import Assistant
from app.models.assistant_workspace_share import AssistantWorkspaceShare
from app.dependencies import get_current_user
from app.models.conversation import Conversation
from app.models.file_attachment import FileAttachment
from app.models.project import WorkspaceProject
from app.models.project_file import ProjectFile
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.projects import ProjectCreate, ProjectOut, ProjectUpdate
from app.schemas.project_validation import ProjectPreviewPlanOut, ProjectValidationItem, ProjectValidationOut

router = APIRouter(prefix="/projects", tags=["Workspace Projects"])


def _get_membership(workspace_id: int, current_user: User, db: Session) -> WorkspaceMember:
    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مساحة العمل غير موجودة",
        )
    return membership


def _get_project(project_id: int, current_user: User, db: Session) -> WorkspaceProject:
    project = db.get(WorkspaceProject, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المشروع غير موجود",
        )
    _get_membership(project.workspace_id, current_user, db)
    return project


def _ensure_unique_name(
    workspace_id: int,
    name: str,
    db: Session,
    exclude_id: int | None = None,
) -> None:
    normalized = name.strip().lower()
    query = db.query(WorkspaceProject).filter(
        WorkspaceProject.workspace_id == workspace_id,
        func.lower(WorkspaceProject.name) == normalized,
    )
    if exclude_id is not None:
        query = query.filter(WorkspaceProject.id != exclude_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="يوجد مشروع بهذا الاسم في مساحة العمل",
        )


def _get_accessible_assistant(
    assistant_id: int, workspace_id: int, current_user: User, db: Session
) -> Assistant:
    assistant = (
        db.query(Assistant)
        .outerjoin(
            AssistantWorkspaceShare,
            (AssistantWorkspaceShare.assistant_id == Assistant.id)
            & (AssistantWorkspaceShare.workspace_id == workspace_id),
        )
        .filter(
            Assistant.id == assistant_id,
            (Assistant.user_id == current_user.id)
            | AssistantWorkspaceShare.id.is_not(None),
        )
        .first()
    )
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المساعد غير موجود",
        )
    return assistant


def _can_manage(project: WorkspaceProject, membership: WorkspaceMember) -> None:
    if membership.role not in {WorkspaceRole.owner, WorkspaceRole.admin}:
        # منشئ المشروع يستطيع إدارة مشروعه.
        if project.owner_id != membership.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="هذه العملية تتطلب صلاحية مدير المشروع أو مساحة العمل",
            )


@router.get("", response_model=list[ProjectOut])
def list_projects(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_membership(workspace_id, current_user, db)
    return (
        db.query(WorkspaceProject)
        .filter(WorkspaceProject.workspace_id == workspace_id)
        .order_by(WorkspaceProject.created_at.asc(), WorkspaceProject.id.asc())
        .all()
    )


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_membership(payload.workspace_id, current_user, db)
    _ensure_unique_name(payload.workspace_id, payload.name, db)

    project = WorkspaceProject(
        workspace_id=payload.workspace_id,
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description.strip() if payload.description else None,
        instructions=payload.instructions.strip() if payload.instructions else None,
    )
    if payload.assistant_id is not None:
        _get_accessible_assistant(payload.assistant_id, payload.workspace_id, current_user, db)
        project.assistant_id = payload.assistant_id
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    membership = _get_membership(project.workspace_id, current_user, db)
    _can_manage(project, membership)
    _ensure_unique_name(project.workspace_id, payload.name, db, exclude_id=project.id)

    project.name = payload.name
    project.description = payload.description.strip() if payload.description else None
    project.instructions = payload.instructions.strip() if payload.instructions else None
    if payload.assistant_id is not None:
        _get_accessible_assistant(payload.assistant_id, project.workspace_id, current_user, db)
    project.assistant_id = payload.assistant_id
    db.commit()
    db.refresh(project)
    return project



@router.get("/{project_id}/validate", response_model=ProjectValidationOut)
def validate_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    files = (
        db.query(ProjectFile)
        .filter(ProjectFile.project_id == project.id)
        .order_by(ProjectFile.path.asc(), ProjectFile.id.asc())
        .all()
    )

    checks: list[ProjectValidationItem] = []

    def add(level: str, code: str, message: str, path: str | None = None):
        checks.append(
            ProjectValidationItem(
                level=level, code=code, message=message, path=path
            )
        )

    if not files:
        add("error", "project_empty", "المشروع لا يحتوي على ملفات مصدر.")
        return ProjectValidationOut(
            project_id=project.id,
            project_kind="unknown",
            files_count=0,
            errors=1,
            warnings=0,
            checks=checks,
        )

    lowered = {item.path.lower(): item for item in files}
    kind = "generic"

    package_file = lowered.get("package.json")
    pyproject_file = lowered.get("pyproject.toml")
    requirements_file = lowered.get("requirements.txt")
    html_file = lowered.get("index.html")

    if package_file:
        kind = "javascript"
        try:
            package_data = json.loads(package_file.content)
            if not isinstance(package_data, dict):
                add(
                    "error",
                    "invalid_package_json",
                    "package.json يجب أن يحتوي على كائن JSON.",
                    package_file.path,
                )
            elif not package_data.get("name"):
                add(
                    "warning",
                    "package_name_missing",
                    "package.json لا يحتوي على name.",
                    package_file.path,
                )
        except json.JSONDecodeError as exc:
            add(
                "error",
                "invalid_package_json",
                f"package.json يحتوي JSON غير صالح: {exc.msg}.",
                package_file.path,
            )

    if lowered.get("package-lock.json") and not package_file:
        lockfile = lowered["package-lock.json"]
        add(
            "error",
            "lockfile_without_manifest",
            "وجد package-lock.json بدون package.json.",
            lockfile.path,
        )

    if pyproject_file or requirements_file:
        kind = "python"

    if pyproject_file:
        try:
            parsed = tomllib.loads(pyproject_file.content)
            if not isinstance(parsed, dict):
                add("error", "invalid_pyproject", "pyproject.toml غير صالح.", pyproject_file.path)
        except tomllib.TOMLDecodeError as exc:
            add(
                "error",
                "invalid_pyproject",
                f"pyproject.toml غير صالح: {exc.msg}.",
                pyproject_file.path,
            )
    elif requirements_file:
        add(
            "warning",
            "requirements_without_pyproject",
            "للمشروع Python لا يوجد pyproject.toml؛ هذا ليس خطأ لكنه يقلل وضوح إعداد المشروع.",
            requirements_file.path,
        )

    if html_file:
        if kind == "generic":
            kind = "web"
        html_lower = html_file.content.lower()
        if "<html" not in html_lower:
            add(
                "warning",
                "html_root_missing",
                "index.html لا يحتوي على عنصر html واضح.",
                html_file.path,
            )
        if "<body" not in html_lower:
            add(
                "warning",
                "html_body_missing",
                "index.html لا يحتوي على عنصر body واضح.",
                html_file.path,
            )

    for item in files:
        path_lower = item.path.lower()
        if "\x00" in item.content:
            add(
                "error",
                "binary_content",
                "يحتوي الملف على NUL bytes؛ احفظ ملفات المصدر كنص فقط.",
                item.path,
            )
        if re.search(r"(^|/)\.env(\.[^./]+)?$", path_lower) and path_lower != ".env.example":
            add(
                "warning",
                "secret_file_name",
                "اسم الملف يبدو ملف أسرار بيئيًا؛ لا تضع مفاتيح أو كلمات مرور حقيقية داخل المشروع.",
                item.path,
            )
        if path_lower.endswith((".pem", ".key", ".p12", ".pfx")):
            add(
                "warning",
                "private_key_file",
                "الملف يبدو مادة مفاتيح/شهادة خاصة؛ لا ترفعه بمحتوى سري حقيقي.",
                item.path,
            )

    if kind == "generic":
        add(
            "warning",
            "project_type_unknown",
            "تعذر تحديد نوع المشروع من الملفات الحالية؛ يمكنك الاستمرار، لكن التحقق المتخصص محدود.",
        )

    return ProjectValidationOut(
        project_id=project.id,
        project_kind=kind,
        files_count=len(files),
        errors=sum(1 for item in checks if item.level == "error"),
        warnings=sum(1 for item in checks if item.level == "warning"),
        checks=checks,
    )



@router.get("/{project_id}/preview-plan", response_model=ProjectPreviewPlanOut)
def project_preview_plan(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    files = (
        db.query(ProjectFile)
        .filter(ProjectFile.project_id == project.id)
        .order_by(ProjectFile.path.asc(), ProjectFile.id.asc())
        .all()
    )

    if not files:
        return ProjectPreviewPlanOut(
            project_id=project.id,
            project_kind="unknown",
            strategy="none",
            status="blocked",
            message="لا توجد ملفات مصدر لبناء معاينة.",
        )

    lowered = {item.path.lower(): item for item in files}
    package_file = lowered.get("package.json")
    validation = validate_project(project_id, current_user, db)

    if validation.errors > 0:
        return ProjectPreviewPlanOut(
            project_id=project.id,
            project_kind=validation.project_kind,
            strategy="none",
            status="blocked",
            message="أصلح أخطاء التحقق قبل إنشاء معاينة.",
        )

    static_candidates = ("dist/index.html", "build/index.html", "public/index.html")
    for candidate in static_candidates:
        if candidate in lowered:
            return ProjectPreviewPlanOut(
                project_id=project.id,
                project_kind=validation.project_kind,
                strategy="static-artifact",
                status="ready",
                entrypoint=candidate,
                artifact_root=candidate.rsplit("/", 1)[0],
                message="يوجد artifact ثابت جاهز للعرض بدون build.",
            )

    if "index.html" in lowered and package_file is None:
        return ProjectPreviewPlanOut(
            project_id=project.id,
            project_kind=validation.project_kind,
            strategy="static-html",
            status="ready",
            entrypoint="index.html",
            artifact_root=".",
            message="المشروع يمكن عرضه مباشرة كـHTML ثابت داخل sandbox.",
        )

    if package_file is not None:
        package_data = {}
        try:
            package_data = json.loads(package_file.content)
        except json.JSONDecodeError:
            pass
        scripts = package_data.get("scripts") if isinstance(package_data, dict) else {}
        has_build = isinstance(scripts, dict) and isinstance(scripts.get("build"), str) and bool(
            scripts.get("build", "").strip()
        )
        return ProjectPreviewPlanOut(
            project_id=project.id,
            project_kind="javascript",
            strategy="javascript-build",
            status="build-required",
            entrypoint="package.json",
            build_command_detected=has_build,
            message=(
                "المشروع يحتاج build معزول قبل المعاينة."
                if has_build
                else "المشروع يحتاج build strategy، لكن package.json لا يعرّف script باسم build."
            ),
        )

    if validation.project_kind == "python":
        return ProjectPreviewPlanOut(
            project_id=project.id,
            project_kind="python",
            strategy="none",
            status="unsupported",
            message="معاينة Python تتطلب runtime معزولًا مستقلًا؛ لا يتم تشغيله داخل خدمة الويب.",
        )

    return ProjectPreviewPlanOut(
        project_id=project.id,
        project_kind=validation.project_kind,
        strategy="none",
        status="unsupported",
        message="لم يتم العثور على artifact ثابت أو استراتيجية build مدعومة لهذا المشروع.",
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    membership = _get_membership(project.workspace_id, current_user, db)
    _can_manage(project, membership)

    db.query(Conversation).filter(
        Conversation.project_id == project.id
    ).update({"project_id": None}, synchronize_session=False)
    db.query(FileAttachment).filter(
        FileAttachment.project_id == project.id
    ).update({"project_id": None}, synchronize_session=False)
    db.delete(project)
    db.commit()
