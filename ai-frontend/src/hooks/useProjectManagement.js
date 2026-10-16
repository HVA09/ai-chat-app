import { useRef } from "react";
import {
  createProject,
  deleteProject,
  exportProject,
  importProject,
  listProjects,
  moveConversationToProject,
  updateProject,
} from "../lib/projectsApi";
import { getErrorMessage } from "../lib/errors";

export default function useProjectManagement({
  projects,
  selectedWorkspaceId,
  projectRequestGenerationRef,
  selectedProjectId,
  selectedFolderId,
  editingProjectId,
  showArchivedConversations,
  conversationId,
  setProjects,
  setSelectedProjectId,
  setSelectedFolderId,
  setSelectedAssistantId,
  setShowProjectEditor,
  setEditingProjectId,
  startNewChat,
  refreshConversations,
  setToast,
  t,
}) {
  const refreshRequestRef = useRef(0);

  const refreshProjects = async (workspaceId = selectedWorkspaceId) => {
    const requestId = ++refreshRequestRef.current;
    const resetGeneration = projectRequestGenerationRef?.current ?? 0;
    const isCurrentRequest = () =>
      requestId === refreshRequestRef.current &&
      resetGeneration === (projectRequestGenerationRef?.current ?? 0);

    if (workspaceId === null || workspaceId === undefined) {
      if (!isCurrentRequest()) return;
      setProjects([]);
      setSelectedProjectId(null);
      return;
    }

    try {
      const list = await listProjects(workspaceId);
      // Workspace switches and logout invalidate requests started for older context.
      if (!isCurrentRequest()) return;
      setProjects(list);
      setSelectedProjectId((current) =>
        current && list.some((project) => project.id === current) ? current : null
      );
    } catch (error) {
      // An outdated failure must not clear the current workspace's projects or toast.
      if (!isCurrentRequest()) return;
      setProjects([]);
      setSelectedProjectId(null);
      setToast({
        message: getErrorMessage(error, t("app.projectLoadError")),
        type: "error",
      });
    }
  };

  const handleSaveProject = async ({ name, description, instructions, assistant_id }) => {
    try {
      if (editingProjectId === null) {
        if (selectedWorkspaceId === null) return;
        const project = await createProject(
          selectedWorkspaceId,
          name,
          description || "",
          instructions || "",
          assistant_id ?? null
        );
        await refreshProjects(selectedWorkspaceId);
        setSelectedProjectId(project.id);
        setSelectedFolderId(null);
        startNewChat();
        await refreshConversations(
          showArchivedConversations,
          null,
          selectedWorkspaceId,
          project.id
        );
      } else {
        const project = await updateProject(
          editingProjectId,
          name,
          description || "",
          instructions || "",
          assistant_id ?? null
        );
        await refreshProjects(selectedWorkspaceId);
        if (selectedProjectId === editingProjectId) {
          setSelectedProjectId(project.id);
        }
        await refreshConversations(
          showArchivedConversations,
          selectedFolderId,
          selectedWorkspaceId,
          selectedProjectId
        );
      }
      setShowProjectEditor(false);
      setEditingProjectId(null);
    } catch (error) {
      setToast({
        message:
          error?.response?.data?.detail ||
          (editingProjectId === null
            ? t("app.projectCreateError")
            : t("app.projectUpdateError")),
        type: "error",
      });
      throw error;
    }
  };

  const handleDeleteProject = async (id, name) => {
    if (!window.confirm(t("sidebar.projectDeleteConfirm", { name }))) return;
    const wasSelected = id === selectedProjectId;
    try {
      await deleteProject(id);
      if (wasSelected) {
        setSelectedProjectId(null);
        startNewChat();
      }
      await refreshProjects(selectedWorkspaceId);
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        wasSelected ? null : selectedProjectId
      );
    } catch (error) {
      setToast({
        message: error?.response?.data?.detail || t("app.projectDeleteError"),
        type: "error",
      });
    }
  };

  const handleSelectProject = async (id) => {
    const project = id === null ? null : projects.find((item) => item.id === Number(id));
    setSelectedProjectId(id);
    setSelectedFolderId(null);
    setSelectedAssistantId(project?.assistant_id ?? null);
    startNewChat();
    await refreshConversations(
      showArchivedConversations,
      null,
      selectedWorkspaceId,
      id
    );
  };

  const handleExportProject = async (projectId) => {
    try {
      const project = projects.find((item) => item.id === Number(projectId));
      const blob = await exportProject(Number(projectId));
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `project-${projectId}-${(project?.name || "export").replace(/[^a-zA-Z0-9_-]+/g, "-")}.zip`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setToast({ message: t("app.projectExportSuccess"), type: "success" });
    } catch (error) {
      setToast({
        message: error?.response?.data?.detail || t("app.projectExportError"),
        type: "error",
      });
    }
  };

  const handleImportProject = async (file) => {
    if (!selectedWorkspaceId || !file) return;
    try {
      let result;
      try {
        result = await importProject(selectedWorkspaceId, file, "fail");
      } catch (error) {
        if (error?.response?.status !== 409) throw error;
        const shouldRename = window.confirm(t("app.projectImportRenameConfirm"));
        if (!shouldRename) return;
        result = await importProject(selectedWorkspaceId, file, "rename");
      }
      await refreshProjects(selectedWorkspaceId);
      setSelectedProjectId(result.project_id);
      setSelectedFolderId(null);
      startNewChat();
      await refreshConversations(
        showArchivedConversations,
        null,
        selectedWorkspaceId,
        result.project_id
      );
      setToast({
        message: t("app.projectImportSuccess", { name: result.name }),
        type: "success",
      });
    } catch (error) {
      setToast({
        message: error?.response?.data?.detail || t("app.projectImportError"),
        type: "error",
      });
    }
  };

  const handleMoveConversationToProject = async (id, projectId) => {
    const normalizedProjectId = projectId === "" ? null : Number(projectId);
    try {
      const result = await moveConversationToProject(id, normalizedProjectId);
      if (
        id === conversationId &&
        selectedProjectId !== null &&
        result.project_id !== selectedProjectId
      ) {
        startNewChat();
      }
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId
      );
    } catch (error) {
      setToast({
        message: error?.response?.data?.detail || t("app.conversationMoveError"),
        type: "error",
      });
    }
  };

  return {
    refreshProjects,
    handleSaveProject,
    handleDeleteProject,
    handleSelectProject,
    handleExportProject,
    handleImportProject,
    handleMoveConversationToProject,
  };
}
