import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createProjectMemory,
  deleteProjectMemory,
  listProjectMemories,
  updateProjectMemory,
} from "../lib/projectMemoriesApi";
import { getErrorMessage } from "../lib/errors";
import {
  createProjectFile,
  deleteProjectFile,
  getProjectFile,
  listProjectFiles,
  updateProjectFile,
} from "../lib/projectFilesApi";
import { buildProjectPreview, getProjectPreviewPlan, validateProject } from "../lib/projectValidationApi";
import { listWorkspaceMembers } from "../lib/workspaceMembersApi";
import {
  addProjectMember,
  listProjectMembers,
  removeProjectMember,
  updateProjectMember,
} from "../lib/projectMembersApi";


function buildProjectFileTree(files) {
  const root = { type: "folder", name: "", children: [] };

  files.forEach((projectFile) => {
    const parts = projectFile.path.split("/").filter(Boolean);
    let current = root;

    parts.forEach((part, index) => {
      const isFile = index === parts.length - 1;
      let child = current.children.find(
        (item) => item.name === part && item.type === (isFile ? "file" : "folder")
      );

      if (!child) {
        child = isFile
          ? { type: "file", name: part, path: projectFile.path, projectFile }
          : { type: "folder", name: part, children: [] };
        current.children.push(child);
      }

      current = child;
    });
  });

  const sortTree = (node) => {
    node.children.sort((a, b) => {
      if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    node.children.filter((child) => child.type === "folder").forEach(sortTree);
  };

  sortTree(root);
  return root.children;
}

function ProjectFileTreeNode({ node, depth, selectedFileId, onSelect }) {
  if (node.type === "folder") {
    return (
      <div className="space-y-1">
        <div
          className="flex items-center gap-1.5 px-2 py-1 text-[11px] font-medium text-slate-500 dark:text-slate-400"
          style={{ paddingInlineStart: `${depth * 12 + 8}px` }}
        >
          <span aria-hidden="true">📁</span>
          <span className="truncate">{node.name}</span>
        </div>
        {node.children.map((child) => (
          <ProjectFileTreeNode
            key={child.type === "file" ? child.projectFile.id : `folder:${child.name}`}
            node={child}
            depth={depth + 1}
            selectedFileId={selectedFileId}
            onSelect={onSelect}
          />
        ))}
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onSelect(node.projectFile)}
      title={node.path}
      className={`flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-start text-xs ${
        selectedFileId === node.projectFile.id
          ? "bg-slate-900 text-white"
          : "text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
      }`}
      style={{ paddingInlineStart: `${depth * 12 + 8}px` }}
    >
      <span aria-hidden="true">📄</span>
      <span className="min-w-0 flex-1 truncate">{node.path}</span>
      <span className="text-[10px] opacity-60">{node.projectFile.content_length}</span>
    </button>
  );
}
export default function ProjectEditor({
  project = null,
  assistants = [],
  currentUserId = null,
  workspaceRole = "member",
  onClose,
  onSave,
}) {
  const { t } = useTranslation();
  const isEditing = Boolean(project);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [assistantId, setAssistantId] = useState("");
  const [validationError, setValidationError] = useState("");
  const [saving, setSaving] = useState(false);
  const [memories, setMemories] = useState([]);
  const [memoryDraft, setMemoryDraft] = useState("");
  const [memoryLoading, setMemoryLoading] = useState(false);
  const [memorySaving, setMemorySaving] = useState(false);
  const [projectFiles, setProjectFiles] = useState([]);
  const [selectedFileId, setSelectedFileId] = useState(null);
  const [filePath, setFilePath] = useState("");
  const [fileContent, setFileContent] = useState("");
  const [fileLoading, setFileLoading] = useState(false);
  const [fileSaving, setFileSaving] = useState(false);
  const [fileDeleting, setFileDeleting] = useState(false);
  const [projectValidation, setProjectValidation] = useState(null);
  const [projectValidationLoading, setProjectValidationLoading] = useState(false);
  const [previewHtml, setPreviewHtml] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewPlan, setPreviewPlan] = useState(null);
  const [previewPlanLoading, setPreviewPlanLoading] = useState(false);
  const [previewBuild, setPreviewBuild] = useState(null);
  const [previewBuildLoading, setPreviewBuildLoading] = useState(false);
  const [previewBuildUrl, setPreviewBuildUrl] = useState("");
  const [previewExecutionUrl, setPreviewExecutionUrl] = useState("");
  const [projectMembers, setProjectMembers] = useState([]);
  const [workspaceMembers, setWorkspaceMembers] = useState([]);
  const [projectMembersLoading, setProjectMembersLoading] = useState(false);
  const [projectMemberSaving, setProjectMemberSaving] = useState(false);
  const [selectedProjectMemberId, setSelectedProjectMemberId] = useState("");
  const [selectedProjectMemberRole, setSelectedProjectMemberRole] = useState("viewer");
  const projectFileTree = useMemo(() => buildProjectFileTree(projectFiles), [projectFiles]);

  useEffect(() => {
    setName(project?.name ?? "");
    setDescription(project?.description ?? "");
    setInstructions(project?.instructions ?? "");
    setAssistantId(project?.assistant_id ? String(project.assistant_id) : "");
    setValidationError("");
    setMemoryDraft("");
    setProjectFiles([]);
    setSelectedFileId(null);
    setFilePath("");
    setFileContent("");
    setProjectValidation(null);
    setPreviewHtml("");
    setPreviewPlan(null);
    setPreviewBuild(null);
    setPreviewBuildUrl("");
    setPreviewExecutionUrl("");

    if (!project) {
      setMemories([]);
      return;
    }

    let cancelled = false;
    setMemoryLoading(true);
    listProjectMemories(project.id)
      .then((items) => {
        if (!cancelled) setMemories(items);
      })
      .catch((error) => {
        if (!cancelled) {
          showErrorToast(error, "projectEditor.memoryLoadError");
        }
      })
      .finally(() => {
        if (!cancelled) setMemoryLoading(false);
      });

    listProjectFiles(project.id)
      .then((items) => {
        if (!cancelled) setProjectFiles(items);
      })
      .catch((error) => {
        if (!cancelled) {
          showErrorToast(error, "projectEditor.fileLoadError");
        }
      });

    setProjectMembersLoading(true);
    Promise.all([
      listProjectMembers(project.id),
      listWorkspaceMembers(project.workspace_id),
    ])
      .then(([memberList, workspaceMemberList]) => {
        if (!cancelled) {
          setProjectMembers(memberList);
          setWorkspaceMembers(workspaceMemberList);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          showErrorToast(error, "projectEditor.membersLoadError");
        }
      })
      .finally(() => {
        if (!cancelled) setProjectMembersLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [project, t]);

  const showErrorToast = (error, fallbackKey) => {
    const message = getErrorMessage(error, t(fallbackKey));
    window.dispatchEvent(
      new CustomEvent("app:toast", {
        detail: { message, type: "error" },
      })
    );
  };

  const submit = async (event) => {
    event.preventDefault();
    const normalizedName = name.trim();
    const normalizedDescription = description.trim();
    const normalizedInstructions = instructions.trim();

    if (!normalizedName) {
      setValidationError(t("projectEditor.requiredError"));
      return;
    }

    setValidationError("");
    setSaving(true);
    try {
      await onSave({
        name: normalizedName,
        description: normalizedDescription || null,
        instructions: normalizedInstructions || null,
        assistant_id: assistantId ? Number(assistantId) : null,
      });
    } finally {
      setSaving(false);
    }
  };

  const currentProjectMembership = projectMembers.find(
    (member) => member.user_id === currentUserId
  );
  const canManageProjectMembers =
    isEditing &&
    (project?.owner_id === currentUserId ||
      workspaceRole === "owner" ||
      workspaceRole === "admin" ||
      currentProjectMembership?.role === "manager");
  const existingProjectUserIds = new Set(
    projectMembers.map((member) => member.user_id)
  );
  const availableWorkspaceMembers = workspaceMembers.filter(
    (member) =>
      member.user_id !== project?.owner_id &&
      !existingProjectUserIds.has(member.user_id)
  );

  const refreshProjectMembers = async () => {
    if (!project) return;
    const [memberList, workspaceMemberList] = await Promise.all([
      listProjectMembers(project.id),
      listWorkspaceMembers(project.workspace_id),
    ]);
    setProjectMembers(memberList);
    setWorkspaceMembers(workspaceMemberList);
  };

  const handleAddProjectMember = async () => {
    if (!project || !selectedProjectMemberId) return;
    setProjectMemberSaving(true);
    try {
      await addProjectMember(
        project.id,
        selectedProjectMemberId,
        selectedProjectMemberRole
      );
      setSelectedProjectMemberId("");
      setSelectedProjectMemberRole("viewer");
      await refreshProjectMembers();
    } catch (error) {
      showErrorToast(error, "projectEditor.memberSaveError");
    } finally {
      setProjectMemberSaving(false);
    }
  };

  const handleUpdateProjectMember = async (member, role) => {
    if (!project || member.id == null) return;
    setProjectMemberSaving(true);
    try {
      await updateProjectMember(project.id, member.id, role);
      await refreshProjectMembers();
    } catch (error) {
      showErrorToast(error, "projectEditor.memberSaveError");
    } finally {
      setProjectMemberSaving(false);
    }
  };

  const handleRemoveProjectMember = async (member) => {
    if (!project || member.id == null) return;
    if (
      !window.confirm(
        t("projectEditor.memberRemoveConfirm", { email: member.email })
      )
    ) {
      return;
    }
    setProjectMemberSaving(true);
    try {
      await removeProjectMember(project.id, member.id);
      await refreshProjectMembers();
    } catch (error) {
      showErrorToast(error, "projectEditor.memberDeleteError");
    } finally {
      setProjectMemberSaving(false);
    }
  };

  const handleAddMemory = async () => {
    const content = memoryDraft.trim();
    if (!isEditing || !content) return;
    setMemorySaving(true);
    try {
      const memory = await createProjectMemory(project.id, content);
      setMemories((current) => [memory, ...current]);
      setMemoryDraft("");
    } catch (error) {
      showErrorToast(error, "projectEditor.memorySaveError");
    } finally {
      setMemorySaving(false);
    }
  };

  const handleEditMemory = async (memory) => {
    if (!isEditing) return;
    const content = window.prompt(
      t("projectEditor.memoryEditPrompt"),
      memory.content
    );
    if (!content?.trim() || content.trim() === memory.content) return;

    setMemorySaving(true);
    try {
      const updated = await updateProjectMemory(
        project.id,
        memory.id,
        content.trim()
      );
      setMemories((current) =>
        current.map((item) => (item.id === updated.id ? updated : item))
      );
    } catch (error) {
      showErrorToast(error, "projectEditor.memorySaveError");
    } finally {
      setMemorySaving(false);
    }
  };

  const handleSelectFile = async (projectFile) => {
    if (!project) return;
    setFileLoading(true);
    try {
      const detail = await getProjectFile(project.id, projectFile.id);
      setSelectedFileId(detail.id);
      setFilePath(detail.path);
      setFileContent(detail.content);
    } catch (error) {
      showErrorToast(error, "projectEditor.fileLoadError");
    } finally {
      setFileLoading(false);
    }
  };

  const handleNewFile = () => {
    setSelectedFileId(null);
    setFilePath("");
    setFileContent("");
  };

  const handlePreviewPlan = async () => {
    if (!project) return;
    setPreviewPlanLoading(true);
    try {
      const result = await getProjectPreviewPlan(project.id);
      setPreviewPlan(result);
    } catch (error) {
      showErrorToast(error, "projectEditor.previewPlanLoadError");
    } finally {
      setPreviewPlanLoading(false);
    }
  };

  const handlePreviewProject = async () => {
    if (!project) return;
    const indexFile = projectFiles.find(
      (item) => item.path.toLowerCase() === "index.html"
    );
    if (!indexFile) return;

    setPreviewLoading(true);
    try {
      const detail = await getProjectFile(project.id, indexFile.id);
      setPreviewHtml(detail.content);
    } catch (error) {
      showErrorToast(error, "projectEditor.previewLoadError");
    } finally {
      setPreviewLoading(false);
    }
  };


  const handleBuildPreview = async () => {
    if (!project) return;
    setPreviewBuildLoading(true);
    try {
      const result = await buildProjectPreview(project.id);
      setPreviewBuild(result);
      setPreviewBuildUrl(result.preview_url ?? "");
    } catch (error) {
      showErrorToast(error, "projectEditor.previewBuildError");
    } finally {
      setPreviewBuildLoading(false);
    }
  };

  const handleValidateProject = async () => {
    if (!project) return;
    setProjectValidationLoading(true);
    try {
      const result = await validateProject(project.id);
      setProjectValidation(result);
    } catch (error) {
      showErrorToast(error, "projectEditor.validationLoadError");
    } finally {
      setProjectValidationLoading(false);
    }
  };

  const handleSaveFile = async () => {
    if (!project) return;
    const normalizedPath = filePath.trim();
    if (!normalizedPath) {
      showErrorToast(null, "projectEditor.filePathRequired");
      return;
    }

    setFileSaving(true);
    try {
      const saved = selectedFileId
        ? await updateProjectFile(
            project.id,
            selectedFileId,
            normalizedPath,
            fileContent
          )
        : await createProjectFile(project.id, normalizedPath, fileContent);
      const items = await listProjectFiles(project.id);
      setProjectFiles(items);
      setSelectedFileId(saved.id);
      setFilePath(saved.path);
      setFileContent(saved.content);
    } catch (error) {
      showErrorToast(error, "projectEditor.fileSaveError");
    } finally {
      setFileSaving(false);
    }
  };

  const handleDeleteFile = async () => {
    if (!project || selectedFileId === null) return;
    const projectFile = projectFiles.find((item) => item.id === selectedFileId);
    if (!projectFile || !window.confirm(
      t("projectEditor.fileDeleteConfirm", { path: projectFile.path })
    )) {
      return;
    }

    setFileDeleting(true);
    try {
      await deleteProjectFile(project.id, selectedFileId);
      const items = await listProjectFiles(project.id);
      setProjectFiles(items);
      setSelectedFileId(null);
      setFilePath("");
      setFileContent("");
    } catch (error) {
      showErrorToast(error, "projectEditor.fileDeleteError");
    } finally {
      setFileDeleting(false);
    }
  };

  const handleDeleteMemory = async (memory) => {
    if (
      !isEditing ||
      !window.confirm(
        t("projectEditor.memoryDeleteConfirm", { content: memory.content })
      )
    ) {
      return;
    }

    setMemorySaving(true);
    try {
      await deleteProjectMemory(project.id, memory.id);
      setMemories((current) =>
        current.filter((item) => item.id !== memory.id)
      );
    } catch (error) {
      showErrorToast(error, "projectEditor.memoryDeleteError");
    } finally {
      setMemorySaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="project-editor-title"
    >
      <form
        onSubmit={submit}
        className="my-8 w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-slate-700 dark:bg-slate-900"
      >
        <div className="mb-5 flex items-center justify-between gap-4">
          <div>
            <h2
              id="project-editor-title"
              className="text-lg font-semibold text-slate-900 dark:text-slate-100"
            >
              {isEditing
                ? t("projectEditor.editTitle")
                : t("projectEditor.createTitle")}
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {t("projectEditor.subtitle")}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={saving || memorySaving || fileSaving || fileDeleting}
            aria-label={t("projectEditor.close")}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50 dark:hover:bg-slate-800"
          >
            ✕
          </button>
        </div>

        <div className="space-y-4">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
              {t("projectEditor.nameLabel")}
            </span>
            <input
              autoFocus
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={120}
              placeholder={t("projectEditor.namePlaceholder")}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
              {t("projectEditor.descriptionLabel")}
            </span>
            <input
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={1000}
              placeholder={t("projectEditor.descriptionPlaceholder")}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
            />
          </label>

          <label className="block">
            <span
              className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200"
              id="project-default-assistant-label"
            >
              {t("projectEditor.assistantLabel")}
            </span>
            <select
              aria-labelledby="project-default-assistant-label"
              value={assistantId}
              onChange={(event) => setAssistantId(event.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
            >
              <option value="">{t("projectEditor.noDefaultAssistant")}</option>
              {assistants.map((assistant) => (
                <option key={assistant.id} value={assistant.id}>
                  {assistant.name}
                </option>
              ))}
            </select>
            <span className="mt-1 block text-xs text-slate-400">
              {t("projectEditor.assistantHint")}
            </span>
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
              {t("projectEditor.instructionsLabel")}
            </span>
            <textarea
              value={instructions}
              onChange={(event) => setInstructions(event.target.value)}
              maxLength={6000}
              rows={8}
              placeholder={t("projectEditor.instructionsPlaceholder")}
              className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
            />
            <span className="mt-1 block text-end text-xs text-slate-400">
              {instructions.length}/6000
            </span>
          </label>

          {isEditing && (
            <section className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {t("projectEditor.membersTitle")}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {t("projectEditor.membersDescription")}
                  </p>
                </div>
                <span className="rounded-full border border-slate-200 px-2 py-1 text-[10px] font-medium text-slate-500 dark:border-slate-700 dark:text-slate-400">
                  {projectMembers.length}
                </span>
              </div>

              {projectMembersLoading ? (
                <p className="mt-3 text-xs text-slate-400">{t("projectEditor.membersLoading")}</p>
              ) : (
                <div className="mt-3 space-y-2">
                  {projectMembers.map((member) => {
                    const rowManager =
                      member.is_owner ||
                      member.role === "manager" ||
                      workspaceRole === "owner" ||
                      workspaceRole === "admin";
                    const roleLabel = member.is_owner
                      ? t("projectEditor.roleOwner")
                      : t("projectEditor.role" + member.role.charAt(0).toUpperCase() + member.role.slice(1));
                    return (
                      <div
                        key={member.id ?? `owner-${member.user_id}`}
                        className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800"
                      >
                        <div className="min-w-0">
                          <div className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">
                            {member.full_name || member.email}
                            {member.user_id === currentUserId && (
                              <span className="ms-2 text-[10px] text-slate-400">{t("projectEditor.membersYou")}</span>
                            )}
                          </div>
                          <div className="truncate text-xs text-slate-500 dark:text-slate-400">{member.email}</div>
                        </div>
                        <div className="flex items-center gap-2">
                          {rowManager && canManageProjectMembers && !member.is_owner ? (
                            <select
                              value={member.role}
                              disabled={projectMemberSaving}
                              onChange={(event) => handleUpdateProjectMember(member, event.target.value)}
                              className="rounded-lg border border-slate-200 px-2 py-1 text-xs dark:border-slate-600 dark:bg-slate-900"
                              aria-label={t("projectEditor.memberRoleLabel", { email: member.email })}
                            >
                              <option value="viewer">{t("projectEditor.roleViewer")}</option>
                              <option value="editor">{t("projectEditor.roleEditor")}</option>
                              <option value="manager">{t("projectEditor.roleManager")}</option>
                            </select>
                          ) : (
                            <span className="rounded-full bg-white px-2 py-1 text-xs text-slate-600 dark:bg-slate-900 dark:text-slate-300">
                              {roleLabel}
                            </span>
                          )}
                          {canManageProjectMembers && !member.is_owner && (
                            <button
                              type="button"
                              disabled={projectMemberSaving}
                              onClick={() => handleRemoveProjectMember(member)}
                              className="rounded-lg px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                            >
                              {t("projectEditor.memberRemove")}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}

                  {projectMembers.length === 0 && (
                    <p className="text-xs text-slate-400">{t("projectEditor.membersEmpty")}</p>
                  )}

                  {canManageProjectMembers && (
                    <div className="mt-3 rounded-xl border border-dashed border-slate-300 p-3 dark:border-slate-700">
                      <div className="grid gap-2 sm:grid-cols-[1fr_auto_auto]">
                        <select
                          value={selectedProjectMemberId}
                          disabled={projectMemberSaving}
                          onChange={(event) => setSelectedProjectMemberId(event.target.value)}
                          className="rounded-xl border border-slate-200 px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-900"
                        >
                          <option value="">{t("projectEditor.memberSelectPlaceholder")}</option>
                          {availableWorkspaceMembers.map((member) => (
                            <option key={member.user_id} value={member.user_id}>
                              {member.full_name || member.email} · {member.email}
                            </option>
                          ))}
                        </select>
                        <select
                          value={selectedProjectMemberRole}
                          disabled={projectMemberSaving}
                          onChange={(event) => setSelectedProjectMemberRole(event.target.value)}
                          className="rounded-xl border border-slate-200 px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-900"
                        >
                          <option value="viewer">{t("projectEditor.roleViewer")}</option>
                          <option value="editor">{t("projectEditor.roleEditor")}</option>
                          <option value="manager">{t("projectEditor.roleManager")}</option>
                        </select>
                        <button
                          type="button"
                          disabled={projectMemberSaving || !selectedProjectMemberId}
                          onClick={handleAddProjectMember}
                          className="rounded-xl bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900"
                        >
                          {projectMemberSaving ? t("projectEditor.memberSaving") : t("projectEditor.memberAdd")}
                        </button>
                      </div>
                      <p className="mt-2 text-[11px] text-slate-400">{t("projectEditor.membersWorkspaceOnly")}</p>
                    </div>
                  )}
                </div>
              )}
            </section>
          )}
          {isEditing && (
            <section className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {t("projectEditor.memoryTitle")}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {t("projectEditor.memoryDescription")}
                  </p>
                </div>
                <span className="text-xs text-slate-400">
                  {memories.length}/50
                </span>
              </div>

              <div className="space-y-2">
                <textarea
                  value={memoryDraft}
                  onChange={(event) => setMemoryDraft(event.target.value)}
                  maxLength={1000}
                  rows={3}
                  placeholder={t("projectEditor.memoryPlaceholder")}
                  className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
                />
                <button
                  type="button"
                  onClick={handleAddMemory}
                  disabled={
                    memorySaving ||
                    !memoryDraft.trim() ||
                    memories.length >= 50
                  }
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  {memorySaving
                    ? t("projectEditor.memorySaving")
                    : t("projectEditor.memoryAdd")}
                </button>
              </div>

              {memoryLoading ? (
                <p className="mt-3 text-xs text-slate-400">
                  {t("projectEditor.memoryLoading")}
                </p>
              ) : memories.length === 0 ? (
                <p className="mt-3 text-xs text-slate-400">
                  {t("projectEditor.memoryEmpty")}
                </p>
              ) : (
                <div className="mt-3 space-y-2">
                  {memories.map((memory) => (
                    <div
                      key={memory.id}
                      className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800"
                    >
                      <p className="whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-200">
                        {memory.content}
                      </p>
                      <div className="mt-2 flex gap-2">
                        <button
                          type="button"
                          onClick={() => handleEditMemory(memory)}
                          disabled={memorySaving}
                          className="rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-white disabled:opacity-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                        >
                          {t("projectEditor.memoryEdit")}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteMemory(memory)}
                          disabled={memorySaving}
                          className="rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                        >
                          {t("projectEditor.memoryDelete")}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

            </section>
          )}

          {isEditing && (
            <section className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {t("projectEditor.filesTitle")}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {t("projectEditor.filesDescription")}
                  </p>
                </div>
                <div className="flex flex-wrap items-center justify-end gap-2">
                  {projectFiles.some(
                    (item) => item.path.toLowerCase() === "index.html"
                  ) && (
                    <button
                      type="button"
                      onClick={handlePreviewProject}
                      disabled={
                        previewLoading || projectValidationLoading || fileSaving || fileDeleting
                      }
                      className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                      {previewLoading
                        ? t("projectEditor.previewing")
                        : t("projectEditor.preview")}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={handlePreviewPlan}
                    disabled={previewPlanLoading || projectValidationLoading || fileSaving || fileDeleting}
                    className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                  >
                    {previewPlanLoading
                      ? t("projectEditor.previewPlanLoading")
                      : t("projectEditor.previewPlan")}
                  </button>

                  {previewPlan?.strategy === "javascript-build" && previewPlan?.status === "build-required" && (
                    <button
                      type="button"
                      onClick={handleBuildPreview}
                      disabled={previewBuildLoading || previewPlanLoading || projectValidationLoading || fileSaving || fileDeleting}
                      className="rounded-lg bg-slate-900 px-2.5 py-1.5 text-xs text-white hover:bg-slate-800 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
                    >
                      {previewBuildLoading
                        ? t("projectEditor.previewBuildLoading")
                        : t("projectEditor.previewBuild")}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={handleValidateProject}
                    disabled={projectValidationLoading || fileSaving || fileDeleting}
                    className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                  >
                    {projectValidationLoading
                      ? t("projectEditor.validating")
                      : t("projectEditor.validate")}
                  </button>
                  <button
                    type="button"
                    onClick={handleNewFile}
                    disabled={fileSaving || fileDeleting}
                    className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                  >
                    {t("projectEditor.fileNew")}
                  </button>
                </div>
              </div>

              {previewPlan && (
                <div className="mb-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h4 className="text-xs font-semibold text-slate-800 dark:text-slate-100">
                        {t("projectEditor.previewPlanTitle")}
                      </h4>
                      <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                        {previewPlan.message}
                      </p>
                    </div>
                    <span className="rounded-full border border-slate-200 px-2 py-1 text-[10px] font-medium text-slate-600 dark:border-slate-700 dark:text-slate-300">
                      {previewPlan.strategy}
                    </span>
                  </div>
                  <div className="mt-2 grid gap-2 text-[11px] text-slate-500 dark:text-slate-400 sm:grid-cols-2">
                    <div>{t("projectEditor.previewPlanStatus")}: {previewPlan.status}</div>
                    <div>
                      {t("projectEditor.previewPlanEntrypoint")}:{" "}
                      {previewPlan.entrypoint ?? t("projectEditor.previewPlanNone")}
                    </div>
                    {previewPlan.build_command_detected && (
                      <div className="sm:col-span-2">
                        {t("projectEditor.previewPlanBuildDetected")}
                      </div>
                    )}
                  </div>
                </div>
              )}


              {previewBuild && (
                <div className="mb-3 rounded-xl border border-emerald-200 bg-emerald-50 p-3 dark:border-emerald-900/60 dark:bg-emerald-950/20">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h4 className="text-xs font-semibold text-emerald-800 dark:text-emerald-300">
                        {t("projectEditor.previewBuildReady")}
                      </h4>
                      <p className="mt-1 text-[11px] text-emerald-700 dark:text-emerald-400">
                        {t("projectEditor.previewBuildDescription")}
                      </p>
                    </div>
                    <span className="rounded-full border border-emerald-300 px-2 py-1 text-[10px] font-medium text-emerald-700 dark:border-emerald-800 dark:text-emerald-300">
                      {previewBuild.entrypoint}
                    </span>
                  </div>
                  <div className="mt-2 text-[11px] text-emerald-700 dark:text-emerald-400">
                    {t("projectEditor.previewBuildSize", {
                      size: previewBuild.artifact_size_bytes,
                    })}
                  </div>
                  <p className="mt-2 text-[11px] text-emerald-700 dark:text-emerald-400">
                    {t("projectEditor.previewBuildSecurity")}
                  </p>
                  {previewBuildUrl && (
                    <button
                      type="button"
                      onClick={() => setPreviewExecutionUrl(previewBuildUrl)}
                      className="mt-3 rounded-lg bg-emerald-700 px-3 py-2 text-[11px] font-medium text-white hover:bg-emerald-800"
                    >
                      {t("projectEditor.previewBuildOpen")}
                    </button>
                  )}
                </div>
              )}

              {projectValidation && (
                <div className="mb-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h4 className="text-xs font-semibold text-slate-800 dark:text-slate-100">
                        {t("projectEditor.validationReady")}
                      </h4>
                      <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                        {t("projectEditor.validationSummary", {
                          errors: projectValidation.errors,
                          warnings: projectValidation.warnings,
                          count: projectValidation.files_count,
                        })}
                      </p>
                    </div>
                    {projectValidation.errors === 0 ? (
                      <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
                        {t("projectEditor.validationClean")}
                      </span>
                    ) : (
                      <span className="text-xs font-medium text-red-600 dark:text-red-400">
                        {projectValidation.errors} {t("projectEditor.validationError")}
                      </span>
                    )}
                  </div>
                  {projectValidation.checks.length > 0 && (
                    <div className="mt-3 space-y-2">
                      {projectValidation.checks.map((item, index) => (
                        <div
                          key={`${item.code}-${item.path ?? "project"}-${index}`}
                          className="rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-2 text-xs dark:border-slate-800 dark:bg-slate-950"
                        >
                          <div className="font-medium text-slate-700 dark:text-slate-200">
                            {item.level === "error"
                              ? t("projectEditor.validationError")
                              : item.level === "warning"
                                ? t("projectEditor.validationWarning")
                                : t("projectEditor.validationInfo")}
                            {item.path ? ` — ${item.path}` : ""}
                          </div>
                          <div className="mt-1 text-slate-500 dark:text-slate-400">
                            {item.message}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="grid gap-3 md:grid-cols-[minmax(0,0.38fr)_minmax(0,0.62fr)]">
                <div className="max-h-72 overflow-y-auto rounded-xl border border-slate-200 p-2 dark:border-slate-700">
                  {projectFiles.length === 0 ? (
                    <p className="px-2 py-6 text-center text-xs text-slate-400">
                      {t("projectEditor.filesEmpty")}
                    </p>
                  ) : (
                    <div className="space-y-1">
                      {projectFileTree.map((node) => (
                        <ProjectFileTreeNode
                          key={node.type === "file" ? node.projectFile.id : `folder:${node.name}`}
                          node={node}
                          depth={0}
                          selectedFileId={selectedFileId}
                          onSelect={handleSelectFile}
                        />
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <label className="block">
                    <span className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
                      {t("projectEditor.filePathLabel")}
                    </span>
                    <input
                      value={filePath}
                      onChange={(event) => setFilePath(event.target.value)}
                      maxLength={512}
                      placeholder={t("projectEditor.filePathPlaceholder")}
                      className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800"
                    />
                  </label>
                  <label className="block">
                    <span className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
                      {t("projectEditor.fileContentLabel")}
                    </span>
                    <textarea
                      value={fileContent}
                      onChange={(event) => setFileContent(event.target.value)}
                      maxLength={50000}
                      rows={14}
                      disabled={fileLoading}
                      placeholder={t("projectEditor.fileContentPlaceholder")}
                      className="w-full resize-y rounded-xl border border-slate-200 bg-slate-950 px-3 py-2 font-mono text-xs leading-5 text-slate-100 outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-700"
                    />
                  </label>
                  {fileLoading && (
                    <p className="text-xs text-slate-400">
                      {t("projectEditor.fileLoading")}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={handleSaveFile}
                      disabled={fileSaving || fileDeleting || fileLoading}
                      className="rounded-xl bg-slate-900 px-3 py-2 text-xs text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {fileSaving
                        ? t("projectEditor.fileSaving")
                        : selectedFileId === null
                          ? t("projectEditor.fileCreate")
                          : t("projectEditor.fileSave")}
                    </button>
                    {selectedFileId !== null && (
                      <button
                        type="button"
                        onClick={handleDeleteFile}
                        disabled={fileSaving || fileDeleting || fileLoading}
                        className="rounded-xl border border-red-200 px-3 py-2 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        {fileDeleting
                          ? t("projectEditor.fileDeleting")
                          : t("projectEditor.fileDelete")}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </section>
          )}

          {validationError && (
            <div
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
            >
              {validationError}
            </div>
          )}
        {(previewHtml || previewExecutionUrl) && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4">
            <div
              className="flex h-[90dvh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900"
              role="dialog"
              aria-modal="true"
              aria-labelledby="project-preview-title"
            >
              <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3 dark:border-slate-700">
                <h3
                  id="project-preview-title"
                  className="text-sm font-semibold text-slate-900 dark:text-slate-100"
                >
                  {t("projectEditor.previewTitle")}
                </h3>
                <button
                  type="button"
                  onClick={() => {
                    setPreviewHtml("");
                    setPreviewExecutionUrl("");
                  }}
                  className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800"
                  aria-label={t("projectEditor.closePreview")}
                >
                  ✕
                </button>
              </div>
              <div className="min-h-0 flex-1 bg-white p-2 dark:bg-slate-950">
                <iframe
                  title={t("projectEditor.previewTitle")}
                  src={previewExecutionUrl || undefined}
                  srcDoc={previewExecutionUrl ? undefined : previewHtml}
                  sandbox={previewExecutionUrl ? "allow-scripts" : ""}
                  referrerPolicy="no-referrer"
                  className="h-full w-full rounded-xl border border-slate-200 bg-white dark:border-slate-700"
                />
              </div>
            </div>
          </div>
        )}

        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={saving || memorySaving || fileSaving || fileDeleting}
            className="rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            {t("projectEditor.cancel")}
          </button>
          <button
            type="submit"
            disabled={saving || memorySaving || fileSaving || fileDeleting}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? t("projectEditor.saving") : t("projectEditor.save")}
          </button>
        </div>
      </form>
    </div>
  );
}
