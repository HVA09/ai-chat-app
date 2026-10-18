import { useCallback, useRef } from "react";
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
  const activeConversationIdRef = useRef(conversationId);
  activeConversationIdRef.current = conversationId;
  const feedbackOperationsRef = useRef(new Map());
  const requestSequenceRef = useRef(0);

  const handleMessageFeedback = useCallback(
    async (index, rating) => {
      if (!conversationId || loading || readOnlyConversation) return;

      const message = messages[index];
      if (!message) return;

      const previousRating = message.feedback ?? null;
      const nextRating = rating === previousRating ? null : rating;
      const operationKey = JSON.stringify([String(conversationId), index]);
      let operationState = feedbackOperationsRef.current.get(operationKey);

      if (!operationState) {
        operationState = {
          confirmedRating: previousRating,
          latestRequestId: 0,
          pendingCount: 0,
          queue: Promise.resolve(),
        };
        feedbackOperationsRef.current.set(operationKey, operationState);
      }

      const requestId = ++requestSequenceRef.current;
      operationState.latestRequestId = requestId;
      operationState.pendingCount += 1;

      setMessages((prev) =>
        prev.map((item, messageIndex) =>
          messageIndex === index ? { ...item, feedback: nextRating } : item
        )
      );

      // Serialize writes for one message so rapid taps cannot persist out of order.
      const operation = operationState.queue.catch(() => undefined).then(async () => {
        try {
          await setMessageFeedback(conversationId, index + 1, nextRating);
          operationState.confirmedRating = nextRating;
        } catch {
          const sameConversation =
            String(activeConversationIdRef.current ?? "") === String(conversationId);
          const isLatestRequest = operationState.latestRequestId === requestId;

          // A late failure from an old conversation or superseded tap must not
          // overwrite newer UI state. Roll back only to the last confirmed rating.
          if (sameConversation && isLatestRequest) {
            setMessages((prev) =>
              prev.map((item, messageIndex) =>
                messageIndex === index
                  ? { ...item, feedback: operationState.confirmedRating }
                  : item
              )
            );
            setToast({ message: t("app.feedbackError"), type: "error" });
          }
        } finally {
          operationState.pendingCount -= 1;
          if (
            operationState.pendingCount === 0 &&
            feedbackOperationsRef.current.get(operationKey) === operationState
          ) {
            feedbackOperationsRef.current.delete(operationKey);
          }
        }
      });

      operationState.queue = operation.catch(() => undefined);
      await operation;
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
