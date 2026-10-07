import { useCallback, useRef } from "react";
import { getConversation, listConversationBranches } from "../lib/conversationsApi";
import { getConversationWorkspaceShare } from "../lib/workspaceConversationSharesApi";
import { getErrorMessage } from "../lib/errors";

export default function useOpenConversation({
  aiModels,
  setConversationId,
  setActiveConversationTitle,
  setParentConversationId,
  setConversationBranches,
  setConversationSummary,
  setConversationSummaryUpdatedAt,
  setSelectedAssistantId,
  setSelectedWorkspaceId,
  setSelectedFolderId,
  setSelectedProjectId,
  setSelectedModel,
  setWorkspaceShare,
  setMessages,
  setSelectedConversationIds,
  setShowShareManager,
  setReadOnlyConversation,
  setShowWorkspaceComments,
  setError,
  setToast,
  setInput,
  resetChatAttachments,
  setEditingMessageIndex,
  setRetryableUserMessage,
  messageCountRef,
  autoSummaryLastMessageCountRef,
  t,
}) {
  const conversationOpenRequestRef = useRef(0);

  const openConversation = useCallback(
    async (id) => {
      const requestId = ++conversationOpenRequestRef.current;
      setConversationId(Number(id));
      setShowShareManager(false);
      setReadOnlyConversation(false);
      setShowWorkspaceComments(false);
      setSelectedConversationIds([]);
      setError("");
      setInput("");
      resetChatAttachments();
      setEditingMessageIndex(null);
      setRetryableUserMessage(null);

      try {
        const data = await getConversation(id);
        if (requestId !== conversationOpenRequestRef.current) return;

        setConversationId(data.id);
        setActiveConversationTitle(data.title || "");
        setParentConversationId(data.parent_conversation_id ?? null);
        messageCountRef.current = data.messages.length;
        autoSummaryLastMessageCountRef.current[data.id] = data.summary
          ? data.messages.length
          : 0;

        try {
          setConversationBranches(await listConversationBranches(data.id));
        } catch {
          setConversationBranches([]);
        }

        setConversationSummary(data.summary ?? null);
        setConversationSummaryUpdatedAt(data.summary_updated_at ?? null);
        setSelectedAssistantId(data.assistant_id ?? null);
        setSelectedWorkspaceId(data.workspace_id ?? null);
        setSelectedFolderId(data.folder_id ?? null);
        setSelectedProjectId(data.project_id ?? null);
        setSelectedModel(
          data.ai_model ||
            aiModels.find((model) => model.is_default)?.id ||
            aiModels[0]?.id ||
            ""
        );

        try {
          setWorkspaceShare(await getConversationWorkspaceShare(data.id));
        } catch {
          setWorkspaceShare(null);
        }

        setMessages(
          data.messages.map((m) => ({
            role: m.role,
            text: m.content,
            time: new Date(m.created_at).toLocaleTimeString(),
            sources: m.sources ?? [],
            feedback: m.feedback ?? null,
            isBookmarked: m.is_bookmarked ?? false,
          }))
        );
      } catch (err) {
        if (requestId !== conversationOpenRequestRef.current) return;
        setError("");
        setToast({
          message: getErrorMessage(err, t("app.conversationLoadError")),
          type: "error",
        });
      }
    },
    [
      aiModels,
      autoSummaryLastMessageCountRef,
      messageCountRef,
      resetChatAttachments,
      setActiveConversationTitle,
      setConversationBranches,
      setConversationId,
      setConversationSummary,
      setConversationSummaryUpdatedAt,
      setEditingMessageIndex,
      setError,
      setInput,
      setMessages,
      setParentConversationId,
      setReadOnlyConversation,
      setRetryableUserMessage,
      setSelectedAssistantId,
      setSelectedConversationIds,
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

  return { openConversation };
}
