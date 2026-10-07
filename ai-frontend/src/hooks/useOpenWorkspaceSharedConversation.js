import { useCallback } from "react";
import { getWorkspaceSharedConversation } from "../lib/workspaceConversationSharesApi";

export default function useOpenWorkspaceSharedConversation({
  setShowShareManager,
  setReadOnlyConversation,
  setShowWorkspaceComments,
  setWorkspaceShare,
  setSelectedWorkspaceId,
  setConversationId,
  setConversationSummary,
  setConversationSummaryUpdatedAt,
  setSelectedAssistantId,
  setSelectedFolderId,
  setSelectedProjectId,
  setSelectedModel,
  setMessages,
  setInput,
  setEditingMessageIndex,
  setError,
  setToast,
  t,
}) {
  const openWorkspaceSharedConversation = useCallback(
    async (workspaceId, sharedConversationId) => {
      try {
        const data = await getWorkspaceSharedConversation(
          Number(workspaceId),
          Number(sharedConversationId)
        );
        setShowShareManager(false);
        setReadOnlyConversation(true);
        setShowWorkspaceComments(true);
        setWorkspaceShare(null);
        setSelectedWorkspaceId(Number(workspaceId));
        setConversationId(data.conversation_id);
        setConversationSummary(null);
        setConversationSummaryUpdatedAt(null);
        setSelectedAssistantId(null);
        setSelectedFolderId(null);
        setSelectedProjectId(null);
        setSelectedModel("");
        setMessages(
          data.messages.map((message) => ({
            role: message.role,
            text: message.content,
            time: new Date(message.created_at).toLocaleTimeString(),
            sources: message.sources ?? [],
            feedback: null,
            isBookmarked: false,
          }))
        );
        setInput("");
        setEditingMessageIndex(null);
        setError("");
      } catch (err) {
        setToast({
          message: err?.response?.data?.detail || t("workspaceSharing.loadError"),
          type: "error",
        });
      }
    },
    [
      setEditingMessageIndex,
      setError,
      setInput,
      setMessages,
      setReadOnlyConversation,
      setSelectedAssistantId,
      setSelectedFolderId,
      setSelectedModel,
      setSelectedProjectId,
      setSelectedWorkspaceId,
      setShowShareManager,
      setShowWorkspaceComments,
      setToast,
      setWorkspaceShare,
      setConversationId,
      setConversationSummary,
      setConversationSummaryUpdatedAt,
      t,
    ]
  );

  return { openWorkspaceSharedConversation };
}
