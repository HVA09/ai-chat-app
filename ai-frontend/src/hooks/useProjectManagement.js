import {
  createProject,
  deleteProject,
  listProjects,
  moveConversationToProject,
  updateProject,
} from "../lib/projectsApi";
import { getErrorMessage } from "../lib/errors";

export default function useProjectManagement({
  projects,
  selectedWorkspaceId,
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
  const refreshProjects = async (workspaceId = selectedWorkspaceId) => {
    if (workspaceId === null || workspaceId === undefined) {
      setProjects([]);
      setSelectedProjectId(null);
      return;
    }

    try {
      const list = await listProjects(workspaceId);
      setProjects(list);
      setSelectedProjectId((current) =>
        current && list.some((project) => project.id === current) ? current : null
      );
    } catch (error) {
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
    handleMoveConversationToProject,
  };
}
