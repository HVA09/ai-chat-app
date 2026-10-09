import { useCallback } from "react";
import { branchConversation } from "../lib/conversationsApi";

export default function useConversationBranching({
  conversationId,
  conversationSearch,
  loading,
  openConversation,
  readOnlyConversation,
  refreshConversations,
  selectedFolderId,
  selectedProjectId,
  selectedTagId,
  selectedWorkspaceId,
  setToast,
  showArchivedConversations,
  showTrashConversations,
  t,
}) {
  const handleBranchConversation = useCallback(
    async (messageIndex) => {
      if (!conversationId || loading || readOnlyConversation) return;

      try {
        const branch = await branchConversation(conversationId, messageIndex + 1);
        await refreshConversations(
          showArchivedConversations,
          selectedFolderId,
          selectedWorkspaceId,
          selectedProjectId,
          conversationSearch,
          showTrashConversations,
          selectedTagId
        );
        await openConversation(branch.id);
        setToast({
          message: t("app.branchConversationSuccess"),
          type: "success",
        });
      } catch (err) {
        setToast({
          message:
            err?.response?.data?.detail || t("app.branchConversationError"),
          type: "error",
        });
      }
    },
    [
      conversationId,
      conversationSearch,
      loading,
      openConversation,
      readOnlyConversation,
      refreshConversations,
      selectedFolderId,
      selectedProjectId,
      selectedTagId,
      selectedWorkspaceId,
      setToast,
      showArchivedConversations,
      showTrashConversations,
      t,
    ]
  );

  return { handleBranchConversation };
}
