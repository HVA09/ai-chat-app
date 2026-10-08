import { useCallback } from "react";
import { streamRegenerateMessage } from "../lib/chatApi";

export default function useRegenerateLastResponse({
  readOnlyConversation,
  conversationId,
  loading,
  lastAssistantIndex,
  messages,
  autoSummaryLastMessageCountRef,
  streamAbortRef,
  messageCountRef,
  setRetryableUserMessage,
  setError,
  setMessages,
  setLoading,
  setConversationId,
  refreshConversations,
  showArchivedConversations,
  selectedFolderId,
  selectedWorkspaceId,
  selectedProjectId,
  maybeAutoSummarizeConversation,
}) {
  const regenerateLastResponse = useCallback(async () => {
    if (
      readOnlyConversation ||
      !conversationId ||
      loading ||
      lastAssistantIndex < 0
    ) {
      return;
    }

    setRetryableUserMessage(null);
    const targetIndex = lastAssistantIndex;
    const previousText = messages[targetIndex]?.text ?? "";
    autoSummaryLastMessageCountRef.current[conversationId] = 0;
    setError("");
    setMessages((prev) =>
      prev.map((message, index) =>
        index === targetIndex
          ? { ...message, text: "", feedback: null }
          : message
      )
    );
    setLoading(true);

    const controller = new AbortController();
    streamAbortRef.current = controller;

    const appendToTargetMessage = (chunk) => {
      setMessages((prev) =>
        prev.map((message, index) =>
          index === targetIndex
            ? { ...message, text: message.text + chunk }
            : message
        )
      );
    };

    await streamRegenerateMessage(conversationId, {
      signal: controller.signal,
      onConversationId: (id) => setConversationId(id),
      onSources: (sources) => {
        setMessages((prev) =>
          prev.map((message, index) =>
            index === targetIndex ? { ...message, sources } : message
          )
        );
      },
      onChunk: appendToTargetMessage,
      onDone: () => {
        streamAbortRef.current = null;
        setLoading(false);
        refreshConversations(
          showArchivedConversations,
          selectedFolderId,
          selectedWorkspaceId,
          selectedProjectId
        );
        void maybeAutoSummarizeConversation(
          conversationId,
          messageCountRef.current
        );
      },
      onError: (message) => {
        streamAbortRef.current = null;
        setLoading(false);
        setError(message);
        setMessages((prev) =>
          prev.map((item, index) =>
            index === targetIndex ? { ...item, text: previousText } : item
          )
        );
      },
    });
  }, [
    autoSummaryLastMessageCountRef,
    conversationId,
    lastAssistantIndex,
    loading,
    maybeAutoSummarizeConversation,
    messages,
    messageCountRef,
    readOnlyConversation,
    refreshConversations,
    selectedFolderId,
    selectedProjectId,
    selectedWorkspaceId,
    setConversationId,
    setError,
    setLoading,
    setMessages,
    setRetryableUserMessage,
    showArchivedConversations,
    streamAbortRef,
  ]);

  return { regenerateLastResponse };
}
