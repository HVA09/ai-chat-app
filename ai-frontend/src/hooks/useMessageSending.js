import { useCallback } from "react";
import { streamChatMessage } from "../lib/chatApi";
import { clearChatDraft } from "../lib/chatDrafts";
import { moveConversationToFolder } from "../lib/conversationsApi";
import { moveConversationToProject } from "../lib/projectsApi";

export default function useMessageSending({
  readOnlyConversation,
  editingMessageIndex,
  editMessage,
  input,
  chatAttachments,
  currentUser,
  conversationId,
  setError,
  setRetryableUserMessage,
  setToolActivity,
  messageCountRef,
  setMessages,
  setInput,
  setLoading,
  streamAbortRef,
  selectedAssistantId,
  selectedWorkspaceId,
  selectedProjectId,
  selectedFolderId,
  selectedModel,
  handleToolEvent,
  setConversationId,
  setToast,
  t,
  messages,
  appendToLastMessage,
  resetChatAttachments,
  setActiveConversationTitle,
  refreshConversations,
  showArchivedConversations,
  maybeAutoGenerateConversationTitle,
  maybeAutoSummarizeConversation,
}) {
  const sendMessage = useCallback(async () => {
    if (readOnlyConversation) return;
    if (editingMessageIndex !== null) {
      await editMessage();
      return;
    }

    const userText = input.trim();
    const fileIds = chatAttachments.map((file) => file.id);
    if (!userText && fileIds.length === 0) return;
    const submittedText =
      userText ||
      (document.documentElement.lang === "ar" ? "أرسل لي الملف المرفق وحلله." : "Please analyze the attached file.");
    clearChatDraft(currentUser?.id, conversationId);
    setError("");
    setRetryableUserMessage(null);
    setToolActivity(null);
    messageCountRef.current += 2;
    setMessages((prev) => [
      ...prev,
      { role: "user", text: submittedText, time: new Date().toLocaleTimeString() },
      { role: "assistant", text: "", time: new Date().toLocaleTimeString(), feedback: null },
    ]);
    setInput("");
    setLoading(true);

    const controller = new AbortController();
    streamAbortRef.current = controller;

    const isNewConversation = !conversationId;
    let createdConversationId = conversationId;
    let receivedFirstChunk = false;

    await streamChatMessage(submittedText, conversationId, selectedAssistantId, {
      signal: controller.signal,
      workspaceId: selectedWorkspaceId,
      projectId: selectedProjectId,
      model: selectedModel || null,
      fileIds,
      onToolEvent: handleToolEvent,
      onConversationId: async (id) => {
        createdConversationId = id;
        setConversationId(id);
        if (isNewConversation && selectedProjectId !== null) {
          try {
            await moveConversationToProject(id, selectedProjectId);
          } catch {
            setToast({ message: t("app.conversationMoveError"), type: "error" });
          }
        } else if (isNewConversation && selectedFolderId !== null) {
          try {
            await moveConversationToFolder(id, selectedFolderId);
          } catch {
            setToast({ message: t("app.conversationMoveError"), type: "error" });
          }
        }
      },
      onSources: (sources) => {
        setMessages((prev) => prev.map((message, index) =>
          index === messages.length + 1 ? { ...message, sources } : message
        ));
      },
      onChunk: (chunk) => {
        if (!receivedFirstChunk) {
          receivedFirstChunk = true;
          // نبقي loading=true أثناء البث عشان زر الإيقاف يظهر
        }
        appendToLastMessage(chunk);
      },
      onDone: async () => {
        streamAbortRef.current = null;
        setLoading(false);
        setRetryableUserMessage(null);
        resetChatAttachments();
        if (isNewConversation) {
          setActiveConversationTitle(submittedText.slice(0, 50));
          refreshConversations(
            showArchivedConversations,
            selectedFolderId,
            selectedWorkspaceId,
            selectedProjectId
          );
          await maybeAutoGenerateConversationTitle(createdConversationId);
        }
        void maybeAutoSummarizeConversation(
          createdConversationId,
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
        const failedConversationId = createdConversationId || conversationId;
        if (failedConversationId) {
          setRetryableUserMessage({
            conversationId: failedConversationId,
            text: submittedText,
          });
        }
      },
    });
  }, [
    readOnlyConversation,
    editingMessageIndex,
    editMessage,
    input,
    chatAttachments,
    currentUser,
    conversationId,
    setError,
    setRetryableUserMessage,
    setToolActivity,
    messageCountRef,
    setMessages,
    setInput,
    setLoading,
    streamAbortRef,
    selectedAssistantId,
    selectedWorkspaceId,
    selectedProjectId,
    selectedFolderId,
    selectedModel,
    handleToolEvent,
    setConversationId,
    setToast,
    t,
    messages,
    appendToLastMessage,
    resetChatAttachments,
    setActiveConversationTitle,
    refreshConversations,
    showArchivedConversations,
    maybeAutoGenerateConversationTitle,
    maybeAutoSummarizeConversation,
  ]);

  return { sendMessage };
}
