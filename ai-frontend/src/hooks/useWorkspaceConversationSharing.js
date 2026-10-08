import { useCallback } from "react";
import {
} from "../lib/workspaceConversationSharesApi";
export default function useWorkspaceConversationSharing({
  conversationId,
  selectedWorkspaceId,
  workspaceShare,
  loading,
  readOnlyConversation,
  openConversation,
  getWorkspaceSharedConversation,
  shareConversationWithWorkspace,
  unshareConversationFromWorkspace,
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
  const handleOpenWorkspaceSharedConversation = useCallback(
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
      setConversationId,
      setConversationSummary,
      setConversationSummaryUpdatedAt,
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
      t,
    ]
  );

  const handleDuplicatedWorkspaceConversation = useCallback(
    async (id) => {
      if (!id) {
        setToast({
          message: t("workspaceSharing.duplicateError"),
          type: "error",
        });
        return;
      }
      try {
        await openConversation(id);
        setReadOnlyConversation(false);
        setToast({
          message: t("workspaceSharing.duplicated"),
          type: "success",
        });
      } catch {
        setToast({
          message: t("workspaceSharing.duplicateError"),
          type: "error",
        });
      }
    },
    [openConversation, setReadOnlyConversation, setToast, t]
  );

  const handleToggleWorkspaceShare = useCallback(
    async () => {
      if (!conversationId || !selectedWorkspaceId || loading || readOnlyConversation) {
        return;
      }
      try {
        if (workspaceShare) {
          await unshareConversationFromWorkspace(conversationId);
          setWorkspaceShare(null);
          setToast({
            message: t("workspaceSharing.unshared"),
            type: "success",
          });
        } else {
          const share = await shareConversationWithWorkspace(conversationId);
          setWorkspaceShare(share);
          setToast({
            message: t("workspaceSharing.shared"),
            type: "success",
          });
        }
      } catch (err) {
        setToast({
          message: err?.response?.data?.detail || t("workspaceSharing.updateError"),
          type: "error",
        });
      }
    },
    [
      conversationId,
      loading,
      readOnlyConversation,
      selectedWorkspaceId,
      setToast,
      setWorkspaceShare,
      t,
      workspaceShare,
    ]
  );

  return {
    handleOpenWorkspaceSharedConversation,
    handleDuplicatedWorkspaceConversation,
    handleToggleWorkspaceShare,
  };
}
