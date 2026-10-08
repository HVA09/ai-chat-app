import { useCallback } from "react";
import {
  generateConversationTitle,
  summarizeConversation,
} from "../lib/conversationsApi";

const AUTO_SUMMARY_MESSAGE_THRESHOLD = 12;

export default function useConversationMetadata({
  conversationId,
  loading,
  titleLoading,
  summaryLoading,
  readOnlyConversation,
  autoGenerateTitles,
  autoGenerateSummaries,
  conversationSearch,
  showArchivedConversations,
  showTrashConversations,
  selectedFolderId,
  selectedWorkspaceId,
  selectedProjectId,
  selectedTagId,
  messageCountRef,
  autoSummaryLastMessageCountRef,
  autoSummaryInFlightRef,
  refreshConversations,
  setConversationSummary,
  setConversationSummaryUpdatedAt,
  setSummaryLoading,
  setTitleLoading,
  setError,
  setToast,
  t,
}) {
  const handleGenerateConversationTitle = useCallback(async () => {
    if (!conversationId || loading || titleLoading || readOnlyConversation) return;
    setTitleLoading(true);
    setError("");
    try {
      const result = await generateConversationTitle(conversationId);
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId,
        conversationSearch,
        showTrashConversations,
        selectedTagId
      );
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
    conversationSearch,
    loading,
    readOnlyConversation,
    refreshConversations,
    selectedFolderId,
    selectedProjectId,
    selectedTagId,
    selectedWorkspaceId,
    setError,
    setTitleLoading,
    setToast,
    showArchivedConversations,
    showTrashConversations,
    t,
    titleLoading,
  ]);

  const maybeAutoGenerateConversationTitle = useCallback(
    async (id) => {
      if (!autoGenerateTitles || !id || titleLoading || readOnlyConversation) return;
      setTitleLoading(true);
      try {
        const result = await generateConversationTitle(id);
        await refreshConversations(
          showArchivedConversations,
          selectedFolderId,
          selectedWorkspaceId,
          selectedProjectId,
          conversationSearch,
          showTrashConversations,
          selectedTagId
        );
        if (result?.title) {
          setToast({ message: result.title, type: "success" });
        }
      } catch {
        // Auto-title is optional; a title-generation failure must not affect the chat response.
      } finally {
        setTitleLoading(false);
      }
    },
    [
      autoGenerateTitles,
      conversationSearch,
      readOnlyConversation,
      refreshConversations,
      selectedFolderId,
      selectedProjectId,
      selectedTagId,
      selectedWorkspaceId,
      setTitleLoading,
      setToast,
      showArchivedConversations,
      showTrashConversations,
      titleLoading,
    ]
  );

  const maybeAutoSummarizeConversation = useCallback(
    async (id, messageCount = messageCountRef.current) => {
      if (
        !autoGenerateSummaries ||
        !id ||
        readOnlyConversation ||
        messageCount < AUTO_SUMMARY_MESSAGE_THRESHOLD ||
        autoSummaryInFlightRef.current
      ) {
        return;
      }

      const lastCount = autoSummaryLastMessageCountRef.current[id] ?? 0;
      if (messageCount - lastCount < AUTO_SUMMARY_MESSAGE_THRESHOLD) return;

      autoSummaryInFlightRef.current = true;
      try {
        const result = await summarizeConversation(id);
        autoSummaryLastMessageCountRef.current[id] = messageCount;
        if (id === conversationId) {
          setConversationSummary(result.summary);
          setConversationSummaryUpdatedAt(result.summary_updated_at);
        }
      } catch {
        // Auto-summary is optional; a summary failure must not affect the chat response.
      } finally {
        autoSummaryInFlightRef.current = false;
      }
    },
    [
      autoGenerateSummaries,
      autoSummaryInFlightRef,
      autoSummaryLastMessageCountRef,
      conversationId,
      messageCountRef,
      readOnlyConversation,
      setConversationSummary,
      setConversationSummaryUpdatedAt,
    ]
  );

  const handleSummarizeConversation = useCallback(async () => {
    if (!conversationId || loading || summaryLoading || readOnlyConversation) return;
    setSummaryLoading(true);
    setError("");
    try {
      const result = await summarizeConversation(conversationId);
      setConversationSummary(result.summary);
      setConversationSummaryUpdatedAt(result.summary_updated_at);
      autoSummaryLastMessageCountRef.current[conversationId] =
        messageCountRef.current;
      setToast({ message: t("summary.saved"), type: "success" });
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("summary.error"),
        type: "error",
      });
    } finally {
      setSummaryLoading(false);
    }
  }, [
    autoSummaryLastMessageCountRef,
    conversationId,
    loading,
    messageCountRef,
    readOnlyConversation,
    setConversationSummary,
    setConversationSummaryUpdatedAt,
    setError,
    setSummaryLoading,
    setToast,
    summaryLoading,
    t,
  ]);

  return {
    handleGenerateConversationTitle,
    maybeAutoGenerateConversationTitle,
    maybeAutoSummarizeConversation,
    handleSummarizeConversation,
  };
}
