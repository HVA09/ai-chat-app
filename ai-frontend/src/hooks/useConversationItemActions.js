import { useCallback } from "react";
import {
  deleteConversation,
  duplicateConversation,
  moveConversationToFolder,
  renameConversation,
  toggleArchiveConversation,
  togglePinConversation,
  toggleTrashConversation,
} from "../lib/conversationsApi";

export default function useConversationItemActions({
  conversationId,
  conversationSearch,
  openConversation,
  refreshConversations,
  selectedFolderId,
  selectedProjectId,
  selectedTagId,
  selectedWorkspaceId,
  setToast,
  showArchivedConversations,
  showTrashConversations,
  startNewChat,
  t,
}) {
  const handleRenameConversation = useCallback(async (id, newTitle) => {
    try {
      await renameConversation(id, newTitle);
      await refreshConversations();
    } catch {
      setToast({ message: t("app.renameConversationError"), type: "error" });
    }
  }, [refreshConversations, setToast, t]);

  const handleTogglePinConversation = useCallback(async (id) => {
    try {
      await togglePinConversation(id);
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId
      );
    } catch {
      setToast({ message: t("app.pinConversationError"), type: "error" });
    }
  }, [
    refreshConversations,
    selectedFolderId,
    selectedProjectId,
    selectedWorkspaceId,
    setToast,
    showArchivedConversations,
    t,
  ]);

  const handleToggleArchiveConversation = useCallback(async (id) => {
    try {
      const result = await toggleArchiveConversation(id);
      if (result.is_archived && id === conversationId) startNewChat();
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId
      );
    } catch {
      setToast({ message: t("app.archiveConversationError"), type: "error" });
    }
  }, [
    conversationId,
    refreshConversations,
    selectedFolderId,
    selectedProjectId,
    selectedWorkspaceId,
    setToast,
    showArchivedConversations,
    startNewChat,
    t,
  ]);

  const handleToggleTrashConversation = useCallback(async (id) => {
    try {
      await toggleTrashConversation(id);
      if (id === conversationId) startNewChat();
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId,
        conversationSearch,
        showTrashConversations
      );
    } catch {
      setToast({ message: t("app.trashConversationError"), type: "error" });
    }
  }, [
    conversationId,
    conversationSearch,
    refreshConversations,
    selectedFolderId,
    selectedProjectId,
    selectedWorkspaceId,
    setToast,
    showArchivedConversations,
    showTrashConversations,
    startNewChat,
    t,
  ]);

  const handleDuplicateConversation = useCallback(async (id) => {
    try {
      const duplicate = await duplicateConversation(id);
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId,
        conversationSearch,
        showTrashConversations,
        selectedTagId
      );
      await openConversation(duplicate.id);
      setToast({ message: t("app.duplicateConversationSuccess"), type: "success" });
    } catch (error) {
      setToast({
        message: error?.response?.data?.detail || t("app.duplicateConversationError"),
        type: "error",
      });
    }
  }, [
    conversationSearch,
    openConversation,
    refreshConversations,
    selectedFolderId,
    selectedProjectId,
    selectedTagId,
    selectedWorkspaceId,
    setToast,
    showArchivedConversations,
    showTrashConversations,
    t,
  ]);

  const handleMoveConversationToFolder = useCallback(async (id, folderId) => {
    const normalizedFolderId = folderId === "" ? null : Number(folderId);
    try {
      const result = await moveConversationToFolder(id, normalizedFolderId);
      if (
        id === conversationId &&
        selectedFolderId !== null &&
        result.folder_id !== selectedFolderId
      ) {
        startNewChat();
      }
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId
      );
    } catch {
      setToast({ message: t("app.conversationMoveError"), type: "error" });
    }
  }, [
    conversationId,
    refreshConversations,
    selectedFolderId,
    selectedProjectId,
    selectedWorkspaceId,
    setToast,
    showArchivedConversations,
    startNewChat,
    t,
  ]);

  const handleDeleteConversation = useCallback(async (id) => {
    try {
      if (showTrashConversations) {
        await deleteConversation(id);
      } else {
        await toggleTrashConversation(id);
      }
      if (id === conversationId) startNewChat();
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId,
        conversationSearch,
        showTrashConversations
      );
    } catch {
      setToast({
        message: showTrashConversations
          ? t("app.deleteConversationError")
          : t("app.trashConversationError"),
        type: "error",
      });
    }
  }, [
    conversationId,
    conversationSearch,
    refreshConversations,
    selectedFolderId,
    selectedProjectId,
    selectedWorkspaceId,
    setToast,
    showArchivedConversations,
    showTrashConversations,
    startNewChat,
    t,
  ]);

  return {
    handleDeleteConversation,
    handleDuplicateConversation,
    handleMoveConversationToFolder,
    handleRenameConversation,
    handleToggleArchiveConversation,
    handleTogglePinConversation,
    handleToggleTrashConversation,
  };
}
