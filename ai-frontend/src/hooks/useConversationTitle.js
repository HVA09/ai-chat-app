import { useCallback, useState } from "react";
import { generateConversationTitle } from "../lib/conversationsApi";

export default function useConversationTitle({
  autoGenerateTitles,
  conversationId,
  conversationSearch,
  loading,
  readOnlyConversation,
  refreshConversations,
  selectedFolderId,
  selectedProjectId,
  selectedTagId,
  selectedWorkspaceId,
  setError,
  setToast,
  showArchivedConversations,
  showTrashConversations,
  t,
}) {
  const [titleLoading, setTitleLoading] = useState(false);

  const refreshConversationTitle = useCallback(async () => {
    await refreshConversations(
      showArchivedConversations,
      selectedFolderId,
      selectedWorkspaceId,
      selectedProjectId,
      conversationSearch,
      showTrashConversations,
      selectedTagId
    );
  }, [
    conversationSearch,
    refreshConversations,
    selectedFolderId,
    selectedProjectId,
    selectedTagId,
    selectedWorkspaceId,
    showArchivedConversations,
    showTrashConversations,
  ]);

  const handleGenerateConversationTitle = useCallback(async () => {
    if (!conversationId || loading || titleLoading || readOnlyConversation) return;
    setTitleLoading(true);
    setError("");
    try {
      const result = await generateConversationTitle(conversationId);
      await refreshConversationTitle();
      setToast({ message: t("conversationTitle.generated"), type: "success" });
      return result;
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("conversationTitle.error"),
        type: "error",
      });
    } finally {
      setTitleLoading(false);
    }
  }, [
    conversationId,
    loading,
    refreshConversationTitle,
    readOnlyConversation,
    setError,
    setToast,
    t,
    titleLoading,
  ]);

  const maybeAutoGenerateConversationTitle = useCallback(async (id) => {
    if (!autoGenerateTitles || !id || titleLoading || readOnlyConversation) {
      return;
    }
    setTitleLoading(true);
    try {
      const result = await generateConversationTitle(id);
      await refreshConversationTitle();
      if (result?.title) {
        setToast({ message: result.title, type: "success" });
      }
    } catch {
      // Auto-title is optional; a title-generation failure must not affect the chat response.
    } finally {
      setTitleLoading(false);
    }
  }, [
    autoGenerateTitles,
    readOnlyConversation,
    refreshConversationTitle,
    setToast,
    titleLoading,
  ]);

  return {
    handleGenerateConversationTitle,
    maybeAutoGenerateConversationTitle,
    titleLoading,
  };
}
