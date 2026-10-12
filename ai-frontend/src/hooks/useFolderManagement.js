import {
  createFolder,
  deleteFolder,
  listFolders,
  moveFolder,
  renameFolder,
} from "../lib/foldersApi";
import { getErrorMessage } from "../lib/errors";

export default function useFolderManagement({
  selectedWorkspaceId,
  selectedFolderId,
  selectedProjectId,
  showArchivedConversations,
  conversationId,
  setFolders,
  setSelectedFolderId,
  setSelectedProjectId,
  startNewChat,
  refreshConversations,
  maybeAutoSummarizeConversation,
  messageCountRef,
  setToast,
  t,
}) {
  const refreshFolders = async (workspaceId = selectedWorkspaceId) => {
    try {
      setFolders(await listFolders(workspaceId));
    } catch (err) {
      setToast({
        message: getErrorMessage(err, t("app.foldersLoadError")),
        type: "error",
      });
    }
  };

  const handleCreateFolder = async () => {
    const name = window.prompt(t("sidebar.folderCreatePrompt"));
    if (!name?.trim()) return;
    try {
      const folder = await createFolder(name.trim(), selectedWorkspaceId);
      await refreshFolders(selectedWorkspaceId);
      setSelectedFolderId(folder.id);
      startNewChat();
      await refreshConversations(
        showArchivedConversations,
        folder.id,
        selectedWorkspaceId,
        null
      );
    } catch {
      setToast({ message: t("app.folderCreateError"), type: "error" });
    }
  };

  const handleRenameFolder = async (id, newName, color = null) => {
    try {
      await renameFolder(id, newName, color);
      await refreshFolders(selectedWorkspaceId);
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId
      );
      // Preserve the existing post-rename metadata refresh behavior during this
      // refactor; review this side effect separately rather than mixing changes.
      void maybeAutoSummarizeConversation(
        conversationId,
        messageCountRef.current
      );
    } catch {
      setToast({ message: t("app.folderRenameError"), type: "error" });
    }
  };

  const handleMoveFolder = async (id, direction) => {
    try {
      await moveFolder(id, direction);
      await refreshFolders(selectedWorkspaceId);
    } catch {
      setToast({ message: t("app.folderReorderError"), type: "error" });
    }
  };

  const handleDeleteFolder = async (id) => {
    const wasSelected = id === selectedFolderId;
    try {
      await deleteFolder(id);
      if (wasSelected) {
        setSelectedFolderId(null);
        startNewChat();
      }
      await refreshFolders(selectedWorkspaceId);
      await refreshConversations(
        showArchivedConversations,
        wasSelected ? null : selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId
      );
    } catch {
      setToast({ message: t("app.folderDeleteError"), type: "error" });
    }
  };

  const handleSelectFolder = async (id) => {
    setSelectedFolderId(id);
    setSelectedProjectId(null);
    startNewChat();
    await refreshConversations(
      showArchivedConversations,
      id,
      selectedWorkspaceId,
      null
    );
  };

  return {
    refreshFolders,
    handleCreateFolder,
    handleRenameFolder,
    handleMoveFolder,
    handleDeleteFolder,
    handleSelectFolder,
  };
}
