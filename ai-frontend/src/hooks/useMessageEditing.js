import { useCallback } from "react";

export default function useMessageEditing({
  readOnlyConversation,
  loading,
  conversationId,
  messages,
  resetChatAttachments,
  setError,
  setRetryableUserMessage,
  setEditingMessageIndex,
  setInput,
}) {
  const startEditingMessage = useCallback(
    (index) => {
      if (
        readOnlyConversation ||
        loading ||
        !conversationId ||
        messages[index]?.role !== "user"
      ) {
        return;
      }

      setError("");
      setRetryableUserMessage(null);
      resetChatAttachments();
      setEditingMessageIndex(index);
      setInput(messages[index]?.text ?? "");
    },
    [
      conversationId,
      loading,
      messages,
      readOnlyConversation,
      resetChatAttachments,
      setEditingMessageIndex,
      setError,
      setInput,
      setRetryableUserMessage,
    ]
  );

  const cancelEditing = useCallback(() => {
    setEditingMessageIndex(null);
    setInput("");
    setError("");
  }, [setEditingMessageIndex, setError, setInput]);

  return { startEditingMessage, cancelEditing };
}
