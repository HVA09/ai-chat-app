import { useCallback } from "react";

export default function useStartNewChat({
  t,
  messageCountRef,
  conversationOpenRequestRef,
  resetChatAttachments,
  setToolActivity,
  setShowShareManager,
  setWorkspaceShare,
  setReadOnlyConversation,
  setShowWorkspaceComments,
  setSelectedConversationIds,
  setConversationId,
  setConversationBranches,
  setParentConversationId,
  setMessages,
  setInput,
  setEditingMessageIndex,
  setError,
  getWelcomeMessage,
}) {
  const startNewChat = useCallback(() => {
    conversationOpenRequestRef.current += 1;
    messageCountRef.current = 1;
    setToolActivity(null);
    setShowShareManager(false);
    setWorkspaceShare(null);
    setReadOnlyConversation(false);
    setShowWorkspaceComments(false);
    setSelectedConversationIds([]);
    setConversationId(null);
    setConversationBranches([]);
    setParentConversationId(null);
    setMessages([getWelcomeMessage(t)]);
    setInput("");
    resetChatAttachments();
    setEditingMessageIndex(null);
    setError("");
  }, [
    conversationOpenRequestRef,
    getWelcomeMessage,
    messageCountRef,
    resetChatAttachments,
    setConversationBranches,
    setConversationId,
    setEditingMessageIndex,
    setError,
    setInput,
    setMessages,
    setParentConversationId,
    setReadOnlyConversation,
    setSelectedConversationIds,
    setShowShareManager,
    setShowWorkspaceComments,
    setToolActivity,
    setWorkspaceShare,
    t,
  ]);

  return { startNewChat };
}
