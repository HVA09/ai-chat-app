import { useCallback } from "react";
import {
  deleteConversation,
  toggleArchiveConversation,
  togglePinConversation,
  toggleTrashConversation,
} from "../lib/conversationsApi";

export default function useConversationItemActions({
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
}) {
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
    handleToggleArchiveConversation,
    handleTogglePinConversation,
    handleToggleTrashConversation,
  };
}
