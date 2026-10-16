import { useRef } from "react";
import {
  createWorkspace,
  listWorkspaces,
  renameWorkspace,
} from "../lib/workspacesApi";
import { getErrorMessage } from "../lib/errors";

export default function useWorkspaceManagement({
  workspaces,
  selectedWorkspaceId,
  workspaceRequestGenerationRef,
  aiModels,
  showArchivedConversations,
  setWorkspaces,
  setSelectedWorkspaceId,
  setSelectedModel,
  setSelectedFolderId,
  setSelectedProjectId,
  startNewChat,
  refreshFolders,
  refreshProjects,
  refreshAssistants,
  refreshConversations,
  setToast,
  t,
}) {
  const refreshRequestRef = useRef(0);

  const beginWorkspaceRequest = () => {
    const requestId = ++refreshRequestRef.current;
    const resetGeneration = workspaceRequestGenerationRef?.current ?? 0;
    return () =>
      requestId === refreshRequestRef.current &&
      resetGeneration === (workspaceRequestGenerationRef?.current ?? 0);
  };

  const refreshWorkspaces = async () => {
    const isCurrentRequest = beginWorkspaceRequest();
    let list;
    try {
      list = await listWorkspaces();
      if (!isCurrentRequest()) return;
    } catch (err) {
      if (!isCurrentRequest()) return;
      setToast({
        message: getErrorMessage(err, t("app.workspacesLoadError")),
        type: "error",
      });
      return;
    }

    setWorkspaces(list);
    const nextId =
      selectedWorkspaceId && list.some((workspace) => workspace.id === selectedWorkspaceId)
        ? selectedWorkspaceId
        : list[0]?.id ?? null;
    setSelectedWorkspaceId(nextId);
    const selectedWorkspace = list.find((workspace) => workspace.id === nextId);
    setSelectedModel(
      selectedWorkspace?.default_ai_model ||
        aiModels.find((model) => model.is_default)?.id ||
        aiModels[0]?.id ||
        ""
    );
    setSelectedFolderId(null);
    setSelectedProjectId(null);
    await refreshFolders(nextId);
    if (!isCurrentRequest()) return;
    await refreshProjects(nextId);
    if (!isCurrentRequest()) return;
    await refreshAssistants(nextId);
    if (!isCurrentRequest()) return;
    await refreshConversations(showArchivedConversations, null, nextId, null);
  };

  const handleCreateWorkspace = async () => {
    const name = window.prompt(t("sidebar.workspaceCreatePrompt"));
    if (!name?.trim()) return;
    try {
      const workspace = await createWorkspace(name.trim());
      const nextList = [...workspaces, workspace];
      setWorkspaces(nextList);
      setSelectedWorkspaceId(workspace.id);
      setSelectedFolderId(null);
      setSelectedProjectId(null);
      startNewChat();
      await refreshFolders(workspace.id);
      await refreshProjects(workspace.id);
      await refreshAssistants(workspace.id);
      await refreshConversations(showArchivedConversations, null, workspace.id, null);
    } catch {
      setToast({ message: t("app.workspaceCreateError"), type: "error" });
    }
  };

  const handleRenameWorkspace = async () => {
    if (selectedWorkspaceId === null) return;
    const current = workspaces.find((workspace) => workspace.id === selectedWorkspaceId);
    const name = window.prompt(
      t("sidebar.workspaceRenamePrompt"),
      current?.name || ""
    );
    if (!name?.trim()) return;
    try {
      const updated = await renameWorkspace(selectedWorkspaceId, name.trim());
      setWorkspaces((prev) =>
        prev.map((workspace) => (workspace.id === updated.id ? updated : workspace))
      );
    } catch {
      setToast({ message: t("app.workspaceRenameError"), type: "error" });
    }
  };

  const handleWorkspaceUpdated = (updated) => {
    setWorkspaces((prev) =>
      prev.map((workspace) =>
        workspace.id === updated.id ? { ...workspace, ...updated } : workspace
      )
    );
    if (updated.id === selectedWorkspaceId && updated.default_ai_model) {
      setSelectedModel(updated.default_ai_model);
    }
    setToast({ message: t("app.workspaceModelUpdated"), type: "success" });
  };

  const handleWorkspaceQuotaUpdated = (updated) => {
    setWorkspaces((prev) =>
      prev.map((workspace) =>
        workspace.id === updated.id ? { ...workspace, ...updated } : workspace
      )
    );
    setToast({ message: t("app.workspaceQuotaUpdated"), type: "success" });
  };

  const handleSelectWorkspace = async (id) => {
    const workspaceId = Number(id);
    if (!workspaceId || workspaceId === selectedWorkspaceId) return;
    const isCurrentRequest = beginWorkspaceRequest();
    const workspace = workspaces.find((item) => item.id === workspaceId);
    setSelectedWorkspaceId(workspaceId);
    setSelectedFolderId(null);
    setSelectedProjectId(null);
    setSelectedModel(
      workspace?.default_ai_model ||
        aiModels.find((model) => model.is_default)?.id ||
        aiModels[0]?.id ||
        ""
    );
    startNewChat();
    await refreshFolders(workspaceId);
    if (!isCurrentRequest()) return;
    await refreshProjects(workspaceId);
    if (!isCurrentRequest()) return;
    await refreshAssistants(workspaceId);
    if (!isCurrentRequest()) return;
    await refreshConversations(showArchivedConversations, null, workspaceId, null);
  };

  return {
    refreshWorkspaces,
    handleCreateWorkspace,
    handleRenameWorkspace,
    handleWorkspaceUpdated,
    handleWorkspaceQuotaUpdated,
    handleSelectWorkspace,
  };
}
