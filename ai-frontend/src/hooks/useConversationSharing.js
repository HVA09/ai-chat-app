import { useCallback } from "react";
import { createConversationShare } from "../lib/sharedConversationsApi";
import {
  shareConversationWithWorkspace,
  unshareConversationFromWorkspace,
  getWorkspaceSharedConversation,
} from "../lib/workspaceConversationSharesApi";

export default function useConversationSharing({
  conversationId,
  selectedWorkspaceId,
  loading,
  readOnlyConversation,
  workspaceShare,
  messages,
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
  setToast,
  openConversation,
  t,
}) {
  const handleShareConversation = useCallback(async () => {
    if (!conversationId) return;

    try {
      const protect = window.confirm(t("sharing.protectConfirm"));
      let password = null;

      if (protect) {
        password = window.prompt(t("sharing.passwordPrompt"));
        if (password === null) return;
        password = password.trim();
        if (password.length < 8) {
          setToast({ message: t("sharing.passwordTooShort"), type: "error" });
          return;
        }
      }

      const share = await createConversationShare(conversationId, 7, password);

      if (navigator.share) {
        try {
          await navigator.share({
            title: messages[0]?.text || t("appName"),
            url: share.url,
          });
          setToast({ message: t("sharing.sharedSuccess"), type: "success" });
          return;
        } catch (err) {
          if (err?.name === "AbortError") return;
        }
      }

      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(share.url);
        setToast({ message: t("sharing.linkCopied"), type: "success" });
        return;
      }

      window.prompt(t("sharing.copyPrompt"), share.url);
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("sharing.createError"),
        type: "error",
      });
    }
  }, [conversationId, messages, setToast, t]);

  const handleManageConversationShares = useCallback(() => {
    if (!conversationId || loading) return;
    setShowShareManager(true);
  }, [conversationId, loading, setShowShareManager]);

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
        setToast(null);
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
      t,
    ]
  );

  const handleDuplicatedWorkspaceConversation = useCallback(
    async (id) => {
      if (!id) {
        setToast({ message: t("workspaceSharing.duplicateError"), type: "error" });
        return;
      }

      try {
        await openConversation(id);
        setReadOnlyConversation(false);
        setToast({ message: t("workspaceSharing.duplicated"), type: "success" });
      } catch {
        setToast({ message: t("workspaceSharing.duplicateError"), type: "error" });
      }
    },
    [openConversation, setReadOnlyConversation, setToast, t]
  );

  const handleToggleWorkspaceShare = useCallback(async () => {
    if (
      !conversationId ||
      !selectedWorkspaceId ||
      loading ||
      readOnlyConversation
    ) {
      return;
    }

    try {
      if (workspaceShare) {
        await unshareConversationFromWorkspace(conversationId);
        setWorkspaceShare(null);
        setToast({ message: t("workspaceSharing.unshared"), type: "success" });
      } else {
        const share = await shareConversationWithWorkspace(conversationId);
        setWorkspaceShare(share);
        setToast({ message: t("workspaceSharing.shared"), type: "success" });
      }
    } catch (err) {
      setToast({
        message:
          err?.response?.data?.detail || t("workspaceSharing.updateError"),
        type: "error",
      });
    }
  }, [
    conversationId,
    loading,
    readOnlyConversation,
    selectedWorkspaceId,
    setToast,
    setWorkspaceShare,
    t,
    workspaceShare,
  ]);

  return {
    handleShareConversation,
    handleManageConversationShares,
    handleOpenWorkspaceSharedConversation,
    handleDuplicatedWorkspaceConversation,
    handleToggleWorkspaceShare,
  };
}
