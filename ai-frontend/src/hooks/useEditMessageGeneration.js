import { useCallback } from "react";
import { streamEditMessage } from "../lib/chatApi";
import { clearChatDraft } from "../lib/chatDrafts";

export default function useEditMessageGeneration({
  readOnlyConversation,
  editingMessageIndex,
  input,
  conversationId,
  userId,
  loading,
  messages,
  autoSummaryLastMessageCountRef,
  setError,
  setRetryableUserMessage,
  messageCountRef,
  setMessages,
  setInput,
  setEditingMessageIndex,
  setLoading,
  streamAbortRef,
  setConversationId,
  handleToolEvent,
  appendToLastMessage,
  setToolActivity,
  refreshConversations,
  showArchivedConversations,
  selectedFolderId,
  selectedWorkspaceId,
  selectedProjectId,
  maybeAutoSummarizeConversation,
}) {
  const editMessage = useCallback(async () => {
    const targetIndex = editingMessageIndex;
    const editedText = input.trim();
    if (readOnlyConversation || targetIndex === null || !conversationId || !editedText || loading) return;

    const userMessageIndex = messages
      .slice(0, targetIndex + 1)
      .filter((message) => message.role === "user").length;
    if (!userMessageIndex) return;

    const previousMessages = messages;
    autoSummaryLastMessageCountRef.current[conversationId] = 0;
    setError("");
    setRetryableUserMessage(null);
    messageCountRef.current = targetIndex + 2;
    clearChatDraft(userId, conversationId);
    setMessages((prev) => [
      ...prev.slice(0, targetIndex + 1).map((message, index) =>
        index === targetIndex ? { ...message, text: editedText } : message
      ),
      { role: "assistant", text: "", time: new Date().toLocaleTimeString(), sources: [] },
    ]);
    setInput("");
    setEditingMessageIndex(null);
    setLoading(true);

    const controller = new AbortController();
    streamAbortRef.current = controller;

    await streamEditMessage(conversationId, userMessageIndex, editedText, {
      signal: controller.signal,
      onConversationId: (id) => setConversationId(id),
      onToolEvent: handleToolEvent,
      onSources: (sources) => {
        setMessages((prev) => prev.map((message, index) =>
          index === targetIndex + 1 ? { ...message, sources } : message
        ));
      },
      onChunk: appendToLastMessage,
      onDone: () => {
        streamAbortRef.current = null;
        setLoading(false);
        refreshConversations(
          showArchivedConversations,
          selectedFolderId,
          selectedWorkspaceId,
          selectedProjectId
        );
        autoSummaryLastMessageCountRef.current[conversationId] = 0;
        void maybeAutoSummarizeConversation(
          conversationId,
          messageCountRef.current
        );
      },
      onError: (message) => {
        streamAbortRef.current = null;
        setLoading(false);
        setToolActivity(null);
        setError(message);
        setMessages(previousMessages);
        setInput(editedText);
        setEditingMessageIndex(targetIndex);
      },
    });
  }, [
    appendToLastMessage,
    autoSummaryLastMessageCountRef,
    conversationId,
    editingMessageIndex,
    handleToolEvent,
    input,
    loading,
    maybeAutoSummarizeConversation,
    messageCountRef,
    messages,
    readOnlyConversation,
    refreshConversations,
    selectedFolderId,
    selectedProjectId,
    selectedWorkspaceId,
    setConversationId,
    setEditingMessageIndex,
    setError,
    setInput,
    setLoading,
    setMessages,
    setRetryableUserMessage,
    setToolActivity,
    showArchivedConversations,
    streamAbortRef,
    userId,
  ]);

  return { editMessage };
}
