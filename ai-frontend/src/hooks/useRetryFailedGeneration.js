import { useCallback } from "react";
import { streamChatMessage, streamRegenerateMessage } from "../lib/chatApi";
import { moveConversationToFolder } from "../lib/conversationsApi";
import { moveConversationToProject } from "../lib/projectsApi";

export default function useRetryFailedGeneration({
  readOnlyConversation,
  loading,
  retryableUserMessage,
  conversationId,
  selectedAssistantId,
  selectedModel,
  setError,
  setLoading,
  setRetryableUserMessage,
  messageCountRef,
  setMessages,
  streamAbortRef,
  setConversationId,
  appendToLastMessage,
  resetChatAttachments,
  setToast,
  setActiveConversationTitle,
  refreshConversations,
  showArchivedConversations,
  selectedFolderId,
  selectedWorkspaceId,
  selectedProjectId,
  conversationSearch,
  showTrashConversations,
  selectedTagId,
  maybeAutoGenerateConversationTitle,
  maybeAutoSummarizeConversation,
  t,
}) {
  const retryFailedGeneration = useCallback(async () => {
    if (readOnlyConversation || loading || !retryableUserMessage) return;

    // A request rejected before the server starts streaming must be sent again
    // with its original file IDs and context. Only a streamed generation error
    // can safely use the regenerate endpoint without creating a duplicate user
    // message. Older retry payloads default to the historical regenerate path.
    const retryMode = retryableUserMessage.retryMode === "send" ? "send" : "regenerate";
    const payloadConversationId = retryableUserMessage.conversationId ?? null;
    if (retryMode === "regenerate" && (!conversationId || payloadConversationId !== conversationId)) {
      return;
    }
    if (retryMode === "send") {
      if (payloadConversationId && conversationId !== payloadConversationId) return;
      if (!payloadConversationId && conversationId) return;
    }

    const requestField = (key, fallback) =>
      Object.prototype.hasOwnProperty.call(retryableUserMessage, key)
        ? retryableUserMessage[key]
        : fallback;

    const targetConversationId = payloadConversationId || conversationId || null;
    const requestText = retryableUserMessage.text;
    const requestAssistantId = requestField("assistantId", selectedAssistantId) ?? null;
    const requestWorkspaceId = requestField("workspaceId", selectedWorkspaceId) ?? null;
    const requestProjectId = requestField("projectId", selectedProjectId) ?? null;
    const requestFolderId = requestField("folderId", selectedFolderId) ?? null;
    const requestModel = requestField("model", selectedModel) || null;
    const requestFileIds = Array.isArray(retryableUserMessage.fileIds)
      ? retryableUserMessage.fileIds
      : [];
    const isNewConversation = requestField("isNewConversation", !targetConversationId) === true;

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
    let createdConversationId = targetConversationId;

    const handleSources = (sources) => {
      setMessages((prev) =>
        prev.map((message, index) =>
          index === prev.length - 1 && message.role === "assistant"
            ? { ...message, sources }
            : message
        )
      );
    };

    const restoreRetryState = (message, nextRetryMode) => {
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
        ...retryableUserMessage,
        conversationId: createdConversationId || targetConversationId,
        retryMode: nextRetryMode,
      });
    };

    const finishRetry = async () => {
      streamAbortRef.current = null;
      setLoading(false);
      setRetryableUserMessage(null);
      resetChatAttachments?.();

      if (retryMode === "send" && isNewConversation && createdConversationId) {
        setActiveConversationTitle?.(requestText.slice(0, 50));
        refreshConversations(
          showArchivedConversations,
          requestFolderId,
          requestWorkspaceId,
          requestProjectId
        );
        await maybeAutoGenerateConversationTitle?.(createdConversationId);
      } else {
        refreshConversations(
          showArchivedConversations,
          selectedFolderId,
          selectedWorkspaceId,
          selectedProjectId,
          conversationSearch,
          showTrashConversations,
          selectedTagId
        );
      }

      void maybeAutoSummarizeConversation(
        createdConversationId || targetConversationId,
        messageCountRef.current
      );
    };

    if (retryMode === "send") {
      await streamChatMessage(requestText, targetConversationId, requestAssistantId, {
        signal: controller.signal,
        workspaceId: requestWorkspaceId,
        projectId: requestProjectId,
        model: requestModel,
        fileIds: requestFileIds,
        onConversationId: async (id) => {
          createdConversationId = id;
          setConversationId(id);

          if (isNewConversation && requestProjectId !== null) {
            try {
              await moveConversationToProject(id, requestProjectId);
            } catch {
              setToast?.({ message: t?.("app.conversationMoveError") || "تعذر نقل المحادثة", type: "error" });
            }
          } else if (isNewConversation && requestFolderId !== null) {
            try {
              await moveConversationToFolder(id, requestFolderId);
            } catch {
              setToast?.({ message: t?.("app.conversationMoveError") || "تعذر نقل المحادثة", type: "error" });
            }
          }
        },
        onSources: handleSources,
        onChunk: appendToLastMessage,
        onDone: finishRetry,
        onError: (message, failure = {}) => {
          restoreRetryState(message, failure.messagePersisted ? "regenerate" : "send");
        },
      });
      return;
    }

    await streamRegenerateMessage(targetConversationId, {
      signal: controller.signal,
      onConversationId: (id) => setConversationId(id),
      onSources: handleSources,
      onChunk: appendToLastMessage,
      onDone: finishRetry,
      onError: (message) => restoreRetryState(message, "regenerate"),
    });
  }, [
    appendToLastMessage,
    conversationId,
    conversationSearch,
    loading,
    maybeAutoGenerateConversationTitle,
    maybeAutoSummarizeConversation,
    messageCountRef,
    readOnlyConversation,
    refreshConversations,
    resetChatAttachments,
    retryableUserMessage,
    selectedAssistantId,
    selectedFolderId,
    selectedModel,
    selectedProjectId,
    selectedTagId,
    selectedWorkspaceId,
    setActiveConversationTitle,
    setConversationId,
    setError,
    setLoading,
    setMessages,
    setRetryableUserMessage,
    setToast,
    showArchivedConversations,
    showTrashConversations,
    streamAbortRef,
    t,
  ]);

  return { retryFailedGeneration };
}
