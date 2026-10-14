import { useCallback } from "react";
import { streamRegenerateMessage } from "../lib/chatApi";

export default function useRetryFailedGeneration({
  readOnlyConversation,
  loading,
  retryableUserMessage,
  conversationId,
  setError,
  setLoading,
  setRetryableUserMessage,
  messageCountRef,
  setMessages,
  streamAbortRef,
  setConversationId,
  appendToLastMessage,
  refreshConversations,
  showArchivedConversations,
  selectedFolderId,
  selectedWorkspaceId,
  selectedProjectId,
  conversationSearch,
  showTrashConversations,
  selectedTagId,
  maybeAutoSummarizeConversation,
}) {
  const retryFailedGeneration = useCallback(async () => {
    if (
      readOnlyConversation ||
      loading ||
      !retryableUserMessage ||
      !conversationId ||
      retryableUserMessage.conversationId !== conversationId
    ) {
      return;
    }

    setError("");
    setLoading(true);
    setRetryableUserMessage(null);
    messageCountRef.current += 1;
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        text: "",
        time: new Date().toLocaleTimeString(),
        feedback: null,
        sources: [],
      },
    ]);

    const controller = new AbortController();
    streamAbortRef.current = controller;
    const targetConversationId = conversationId;

    await streamRegenerateMessage(targetConversationId, {
      signal: controller.signal,
      onConversationId: (id) => setConversationId(id),
      onSources: (sources) => {
        setMessages((prev) =>
          prev.map((message, index) =>
            index === prev.length - 1 && message.role === "assistant"
              ? { ...message, sources }
              : message
          )
        );
      },
      onChunk: appendToLastMessage,
      onDone: () => {
        streamAbortRef.current = null;
        setLoading(false);
        refreshConversations(
          showArchivedConversations,
          selectedFolderId,
          selectedWorkspaceId,
          selectedProjectId,
          conversationSearch,
          showTrashConversations,
          selectedTagId
        );
        void maybeAutoSummarizeConversation(
          targetConversationId,
          messageCountRef.current
        );
      },
      onError: (message) => {
        streamAbortRef.current = null;
        setLoading(false);
        setError(message);
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && last.text === "") {
            const next = prev.slice(0, -1);
            messageCountRef.current = next.length;
            return next;
          }
          messageCountRef.current = prev.length;
          return prev;
        });
        setRetryableUserMessage({
          conversationId: targetConversationId,
          text: retryableUserMessage.text,
        });
      },
    });
  }, [
    appendToLastMessage,
    conversationId,
    conversationSearch,
    loading,
    maybeAutoSummarizeConversation,
    messageCountRef,
    readOnlyConversation,
    refreshConversations,
    retryableUserMessage,
    selectedFolderId,
    selectedProjectId,
    selectedTagId,
    selectedWorkspaceId,
    setConversationId,
    setError,
    setLoading,
    setMessages,
    setRetryableUserMessage,
    showArchivedConversations,
    showTrashConversations,
    streamAbortRef,
  ]);

  return { retryFailedGeneration };
}
