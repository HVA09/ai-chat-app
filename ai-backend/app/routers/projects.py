"""مسارات المشاريع داخل مساحات العمل."""
import json
import re
import tomllib
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.assistant import Assistant
from app.models.assistant_workspace_share import AssistantWorkspaceShare
from app.dependencies import get_current_user
from app.models.conversation import Conversation
from app.models.file_attachment import FileAttachment
from app.models.project import WorkspaceProject
from app.models.project_file import ProjectFile
from app.models.project_memory import ProjectMemory
from app.models.project_member import ProjectMember, ProjectMemberRole
from app.models.project_artifact import ProjectArtifact
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.projects import ProjectCreate, ProjectOut, ProjectUpdate
from app.schemas.project_members import ProjectMemberCreate, ProjectMemberOut, ProjectMemberUpdate
from app.schemas.project_archive import ProjectImportResult, ProjectImportConflict
from app.schemas.project_artifacts import ProjectArtifactCleanupResult, ProjectArtifactOut
from app.schemas.project_preview import PreviewBuildFile, PreviewBuildResponse
from app.schemas.project_validation import ProjectPreviewPlanOut, ProjectValidationItem, ProjectValidationOut
from app.services.project_preview_artifacts import (
    PreviewArtifactError,
    preview_csp,
    preview_url_path,
    publish_preview_artifact,
    read_preview_file,
    rewrite_absolute_preview_urls,
    verify_preview_token,
)
from app.services.project_access import can_edit_project, can_manage_project, can_read_project
from app.services.project_preview_builder import PreviewBuilderError, build_javascript_preview
from app.services.project_archive import ProjectArchiveError, build_project_export, parse_project_import
from app.audit import log_event

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
    if not can_read_project(project, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المشروع غير موجود",
        )
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


def _can_manage(project: WorkspaceProject, membership: WorkspaceMember, db: Session) -> None:
    if not can_manage_project(project, membership.user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذه العملية تتطلب مدير المشروع أو صلاحية إدارة المشاريع.",
        )


@router.get("", response_model=list[ProjectOut])
def list_projects(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = _get_membership(workspace_id, current_user, db)
    query = db.query(WorkspaceProject).filter(
        WorkspaceProject.workspace_id == workspace_id
    )
    from app.services.workspace_rbac import has_workspace_permission
    if not has_workspace_permission(db, membership, "projects.manage"):
        query = (
            query.outerjoin(ProjectMember, ProjectMember.project_id == WorkspaceProject.id)
            .filter(
                (WorkspaceProject.owner_id == current_user.id)
                | (ProjectMember.user_id == current_user.id)
            )
        )
    return (
        query.order_by(WorkspaceProject.created_at.asc(), WorkspaceProject.id.asc())
        .distinct()
        .all()
    )


@router.post("/import", response_model=ProjectImportResult, status_code=status.HTTP_201_CREATED)
async def import_project(
    workspace_id: int = Form(...),
    on_conflict: ProjectImportConflict = Form("fail"),
    archive: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_membership(workspace_id, current_user, db)
    try:
        imported = parse_project_import(archive.file)
    except ProjectArchiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    requested_name = imported.manifest.project["name"]
    name = requested_name
    if db.query(WorkspaceProject).filter(
        WorkspaceProject.workspace_id == workspace_id,
        func.lower(WorkspaceProject.name) == name.lower(),
    ).first():
        if on_conflict == "fail":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="يوجد مشروع بنفس الاسم داخل مساحة العمل.",
            )
        base = f"{requested_name} (imported)"
        name = base[:120]
        index = 2
        while db.query(WorkspaceProject).filter(
            WorkspaceProject.workspace_id == workspace_id,
            func.lower(WorkspaceProject.name) == name.lower(),
        ).first():
            suffix = f" ({index})"
            name = f"{requested_name[: max(1, 120 - len(suffix))]}{suffix}"
            index += 1

    project = WorkspaceProject(
        workspace_id=workspace_id,
        owner_id=current_user.id,
        name=name,
        description=imported.manifest.project.get("description"),
        instructions=imported.manifest.project.get("instructions"),
    )
    db.add(project)
    db.flush()

    for path, content in imported.files:
        db.add(
            ProjectFile(
                project_id=project.id,
                path=path,
                content=content,
            )
        )
    for content in imported.memories:
        db.add(
            ProjectMemory(
                project_id=project.id,
                created_by_user_id=current_user.id,
                content=content,
            )
        )

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="تعذر إنشاء المشروع المستورد بسبب تعارض بيانات.",
        ) from exc

    db.refresh(project)
    log_event(
        db,
        "project_imported",
        f"استيراد المشروع {project.name} من حزمة version {imported.manifest.schema_version}",
        current_user.id,
        workspace_id,
    )
    return ProjectImportResult(
        project_id=project.id,
        workspace_id=workspace_id,
        name=project.name,
        files_imported=len(imported.files),
        memories_imported=len(imported.memories),
        conflict_policy=on_conflict,
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


@router.get("/{project_id}/export")
def export_project(
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
    memories = (
        db.query(ProjectMemory)
        .filter(ProjectMemory.project_id == project.id)
        .order_by(ProjectMemory.id.asc())
        .all()
    )
    try:
        payload = build_project_export(project, files, memories)
    except ProjectArchiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    filename = f"project-{project.id}-export.zip"
    return StreamingResponse(
        iter([payload]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Project-Archive-Schema": "1",
            "Content-Length": str(len(payload)),
        },
    )


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    membership = _get_membership(project.workspace_id, current_user, db)
    _can_manage(project, membership, db)
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



@router.get("/{project_id}/members", response_model=list[ProjectMemberOut])
def list_project_members(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    owner = db.get(User, project.owner_id)
    rows = (
        db.query(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .filter(ProjectMember.project_id == project.id)
        .order_by(ProjectMember.created_at.asc(), ProjectMember.id.asc())
        .all()
    )
    result = []
    if owner is not None:
        result.append(
            ProjectMemberOut(
                id=None,
                project_id=project.id,
                user_id=owner.id,
                email=owner.email,
                full_name=owner.full_name,
                role=ProjectMemberRole.manager,
                created_at=project.created_at,
                is_owner=True,
            )
        )
    result.extend(
        ProjectMemberOut(
            id=member.id,
            project_id=project.id,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=member.role,
            created_at=member.created_at,
            is_owner=False,
        )
        for member, user in rows
    )
    return result


@router.post("/{project_id}/members", response_model=ProjectMemberOut, status_code=status.HTTP_201_CREATED)
def add_project_member(
    project_id: int,
    payload: ProjectMemberCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    membership = _get_membership(project.workspace_id, current_user, db)
    _can_manage(project, membership, db)

    target_membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == project.workspace_id,
            WorkspaceMember.user_id == payload.user_id,
        )
        .first()
    )
    if target_membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المستخدم ليس عضوًا في مساحة العمل.",
        )
    if payload.user_id == project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="مالك المشروع عضو ضمني ولا يحتاج إضافة.",
        )
    existing = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == payload.user_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="المستخدم عضو بالفعل في المشروع.",
        )

    target = db.get(User, payload.user_id)
    member = ProjectMember(
        project_id=project.id,
        user_id=payload.user_id,
        role=payload.role,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    log_event(
        db,
        "project_member_added",
        f"إضافة {target.email if target else payload.user_id} إلى المشروع {project.id} بدور {payload.role.value}",
        current_user.id,
        project.workspace_id,
    )
    return ProjectMemberOut(
        id=member.id,
        project_id=project.id,
        user_id=target.id,
        email=target.email,
        full_name=target.full_name,
        role=member.role,
        created_at=member.created_at,
        is_owner=False,
    )


@router.patch("/{project_id}/members/{member_id}", response_model=ProjectMemberOut)
def update_project_member(
    project_id: int,
    member_id: int,
    payload: ProjectMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    membership = _get_membership(project.workspace_id, current_user, db)
    _can_manage(project, membership, db)
    member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.id == member_id,
            ProjectMember.project_id == project.id,
        )
        .first()
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="عضو المشروع غير موجود",
        )
    member.role = payload.role
    db.commit()
    db.refresh(member)
    target = db.get(User, member.user_id)
    return ProjectMemberOut(
        id=member.id,
        project_id=project.id,
        user_id=member.user_id,
        email=target.email,
        full_name=target.full_name,
        role=member.role,
        created_at=member.created_at,
        is_owner=False,
    )


@router.delete("/{project_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_member(
    project_id: int,
    member_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    membership = _get_membership(project.workspace_id, current_user, db)
    _can_manage(project, membership, db)
    member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.id == member_id,
            ProjectMember.project_id == project.id,
        )
        .first()
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="عضو المشروع غير موجود",
        )
    db.delete(member)
    db.commit()
    log_event(
        db,
        "project_member_removed",
        f"إزالة المستخدم {member.user_id} من المشروع {project.id}",
        current_user.id,
        project.workspace_id,
    )


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



MAX_PREVIEW_ARTIFACT_HISTORY = 5


def _ensure_project_edit_access(
    project: WorkspaceProject,
    membership: WorkspaceMember,
    db: Session,
) -> None:
    if not can_edit_project(project, membership.user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="تعديل artifacts المشروع يتطلب دور محرر أو مدير المشروع.",
        )


def _cleanup_project_artifacts(db: Session, project_id: int) -> int:
    artifacts = (
        db.query(ProjectArtifact)
        .filter(ProjectArtifact.project_id == project_id)
        .order_by(ProjectArtifact.created_at.desc(), ProjectArtifact.id.desc())
        .all()
    )
    now = int(time.time())
    candidates = [
        artifact
        for index, artifact in enumerate(artifacts)
        if artifact.expires_at <= now or index >= MAX_PREVIEW_ARTIFACT_HISTORY
    ]
    removed = 0
    for artifact in candidates:
        try:
            delete_preview_artifact(project_id, artifact.artifact_id)
        except PreviewArtifactError:
            continue
        db.delete(artifact)
        removed += 1
    if removed:
        db.commit()
    return removed


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




@router.post("/{project_id}/preview-build", response_model=PreviewBuildResponse)
async def build_project_preview(
    project_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    validation = validate_project(project_id, current_user, db)
    if validation.errors > 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="أصلح أخطاء التحقق قبل إنشاء المعاينة.",
        )
    if validation.project_kind != "javascript":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="المعاينة التنفيذية متاحة حاليًا لمشاريع JavaScript فقط.",
        )

    files = (
        db.query(ProjectFile)
        .filter(ProjectFile.project_id == project.id)
        .order_by(ProjectFile.path.asc(), ProjectFile.id.asc())
        .all()
    )
    payload_files = [
        PreviewBuildFile(path=item.path, content=item.content)
        for item in files
    ]
    try:
        build = await build_javascript_preview(project.id, payload_files)
        published = publish_preview_artifact(project.id, build)
    except (PreviewBuilderError, PreviewArtifactError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="خدمة بناء أو نشر المعاينة غير متاحة أو رفضت الطلب.",
        ) from exc

    artifact = (
        db.query(ProjectArtifact)
        .filter(
            ProjectArtifact.project_id == project.id,
            ProjectArtifact.artifact_id == published.artifact_id,
        )
        .first()
    )
    if artifact is None:
        artifact = ProjectArtifact(
            project_id=project.id,
            artifact_id=published.artifact_id,
            entrypoint=published.entrypoint,
            artifact_size_bytes=build.artifact_size_bytes,
            expires_at=published.expires_at,
        )
        db.add(artifact)
    else:
        artifact.entrypoint = published.entrypoint
        artifact.artifact_size_bytes = build.artifact_size_bytes
        artifact.expires_at = published.expires_at
    db.commit()
    _cleanup_project_artifacts(db, project.id)

    preview_path = preview_url_path(
        project.id,
        published.artifact_id,
        published.token,
        published.entrypoint,
    )
    return build.model_copy(
        update={
            "preview_url": str(request.base_url).rstrip("/") + preview_path,
            "preview_expires_at": published.expires_at,
        }
    )
@router.get(
    "/{project_id}/preview-artifacts/{artifact_id}/{token}/{path:path}",
    name="serve_preview_artifact",
)
def serve_preview_artifact(
    project_id: int,
    artifact_id: str,
    token: str,
    path: str,
    db: Session = Depends(get_db),
):
    tracked = (
        db.query(ProjectArtifact)
        .filter(
            ProjectArtifact.project_id == project_id,
            ProjectArtifact.artifact_id == artifact_id,
        )
        .first()
    )
    if not tracked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المعاينة غير متاحة أو انتهت صلاحيتها.",
        )
    try:
        artifact_root = verify_preview_token(project_id, artifact_id, token)
        content, content_type = read_preview_file(project_id, artifact_id, path)
    except PreviewArtifactError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="المعاينة غير متاحة أو انتهت صلاحيتها.",
        ) from exc

    if content_type == "text/html":
        content = rewrite_absolute_preview_urls(
            content.decode("utf-8", errors="strict"),
            project_id,
            artifact_id,
            token,
            artifact_root,
        ).encode("utf-8")

    headers = {
        "Content-Security-Policy": preview_csp(settings.CORS_ORIGINS),
        "Cache-Control": "private, max-age=300",
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=content, media_type=content_type, headers=headers)


@router.get(
    "/{project_id}/preview-artifacts",
    response_model=list[ProjectArtifactOut],
)
def list_preview_artifacts(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    return (
        db.query(ProjectArtifact)
        .filter(ProjectArtifact.project_id == project.id)
        .order_by(ProjectArtifact.created_at.desc(), ProjectArtifact.id.desc())
        .limit(MAX_PREVIEW_ARTIFACT_HISTORY)
        .all()
    )


@router.delete(
    "/{project_id}/preview-artifacts/{artifact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_preview_artifact_route(
    project_id: int,
    artifact_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    membership = _get_membership(project.workspace_id, current_user, db)
    _ensure_project_edit_access(project, membership, db)
    artifact = (
        db.query(ProjectArtifact)
        .filter(
            ProjectArtifact.project_id == project.id,
            ProjectArtifact.artifact_id == artifact_id,
        )
        .first()
    )
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="artifact المعاينة غير موجود.",
        )
    try:
        delete_preview_artifact(project.id, artifact.artifact_id)
    except PreviewArtifactError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="تعذر حذف artifact المعاينة.",
        ) from exc
    db.delete(artifact)
    db.commit()
    log_event(
        db,
        "project_preview_artifact_deleted",
        f"حذف artifact {artifact_id} من المشروع {project.name}",
        current_user.id,
        project.workspace_id,
    )


@router.post(
    "/{project_id}/preview-artifacts/cleanup",
    response_model=ProjectArtifactCleanupResult,
)
def cleanup_preview_artifacts(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    membership = _get_membership(project.workspace_id, current_user, db)
    _can_manage(project, membership, db)
    removed = _cleanup_project_artifacts(db, project.id)
    remaining = db.query(ProjectArtifact).filter(
        ProjectArtifact.project_id == project.id
    ).count()
    if removed:
        log_event(
            db,
            "project_preview_artifacts_cleaned",
            f"تنظيف {removed} artifact من المشروع {project.name}",
            current_user.id,
            project.workspace_id,
        )
    return ProjectArtifactCleanupResult(removed=removed, remaining=remaining)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, current_user, db)
    membership = _get_membership(project.workspace_id, current_user, db)
    _can_manage(project, membership, db)

    db.query(Conversation).filter(
        Conversation.project_id == project.id
    ).update({"project_id": None}, synchronize_session=False)
    db.query(FileAttachment).filter(
        FileAttachment.project_id == project.id
    ).update({"project_id": None}, synchronize_session=False)
    db.delete(project)
    db.commit()
