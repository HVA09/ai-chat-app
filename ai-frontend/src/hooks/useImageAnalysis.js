import { useCallback } from "react";

export default function useImageAnalysis({
  analyzeImage,
  conversationId,
  loading,
  readOnlyConversation,
  messageCountRef,
  setError,
  setShowFiles,
  setMessages,
  setConversationId,
  setLoading,
  refreshConversations,
  showArchivedConversations,
  selectedFolderId,
  selectedWorkspaceId,
  selectedProjectId,
  maybeAutoSummarizeConversation,
  setToast,
  t,
}) {
  const handleAnalyzeImage = useCallback(
    async (file, prompt) => {
      if (!conversationId || loading || readOnlyConversation) return;

      setError("");
      setShowFiles(false);

      const imageMessageCount = messageCountRef.current + 2;
      messageCountRef.current = imageMessageCount;

      setMessages((prev) => [
        ...prev,
        {
          role: "user",
          text: "[صورة: " + file.original_filename + "] " + prompt,
          time: new Date().toLocaleTimeString(),
        },
        {
          role: "assistant",
          text: "",
          time: new Date().toLocaleTimeString(),
        },
      ]);
      setLoading(true);

      try {
        const result = await analyzeImage(conversationId, file.id, prompt);
        setConversationId(result.conversation_id);
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = {
            ...next[next.length - 1],
            text: result.reply,
          };
          return next;
        });
        await refreshConversations(
          showArchivedConversations,
          selectedFolderId,
          selectedWorkspaceId,
          selectedProjectId
        );
        void maybeAutoSummarizeConversation(
          conversationId,
          imageMessageCount
        );
      } catch (err) {
        messageCountRef.current = Math.max(0, messageCountRef.current - 2);
        setMessages((prev) => prev.slice(0, -2));
        setToast({ message: t("app.imageAnalyzeError"), type: "error" });
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [
      analyzeImage,
      conversationId,
      loading,
      maybeAutoSummarizeConversation,
      messageCountRef,
      readOnlyConversation,
      refreshConversations,
      selectedFolderId,
      selectedProjectId,
      selectedWorkspaceId,
      setConversationId,
      setError,
      setLoading,
      setMessages,
      setShowFiles,
      setToast,
      showArchivedConversations,
      t,
    ]
  );

  return { handleAnalyzeImage };
}
