import { useCallback } from "react";
import { setMessageFeedback } from "../lib/chatApi";

export default function useMessageFeedback({
  conversationId,
  loading,
  readOnlyConversation,
  messages,
  setMessages,
  setToast,
  t,
}) {
  const handleMessageFeedback = useCallback(
    async (index, rating) => {
      if (!conversationId || loading || readOnlyConversation) return;

      const nextRating = rating === messages[index]?.feedback ? null : rating;
      const previousRating = messages[index]?.feedback ?? null;

      setMessages((prev) =>
        prev.map((message, messageIndex) =>
          messageIndex === index ? { ...message, feedback: nextRating } : message
        )
      );

      try {
        await setMessageFeedback(conversationId, index + 1, nextRating);
      } catch {
        setMessages((prev) =>
          prev.map((message, messageIndex) =>
            messageIndex === index
              ? { ...message, feedback: previousRating }
              : message
          )
        );
        setToast({ message: t("app.feedbackError"), type: "error" });
      }
    },
    [
      conversationId,
      loading,
      messages,
      readOnlyConversation,
      setMessages,
      setToast,
      t,
    ]
  );

  return { handleMessageFeedback };
}
