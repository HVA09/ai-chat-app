import { useCallback, useEffect, useRef } from "react";

const BOTTOM_THRESHOLD_PX = 96;

/**
 * Keep the conversation pinned to the latest message only while the user is
 * already near the bottom. A new conversation or a newly submitted user
 * message always starts at the latest content.
 */
export default function useChatAutoScroll({ conversationId, messages, loading }) {
  const scrollContainerRef = useRef(null);
  const shouldFollowRef = useRef(true);
  const previousStateRef = useRef({ conversationId: null, messageCount: 0 });

  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    shouldFollowRef.current = distanceFromBottom <= BOTTOM_THRESHOLD_PX;
  }, []);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const previous = previousStateRef.current;
    const conversationChanged = previous.conversationId !== conversationId;
    const latestMessage = messages[messages.length - 1];
    const addedUserMessage =
      previous.conversationId === conversationId &&
      messages.length > previous.messageCount &&
      latestMessage?.role === "user";

    if (conversationChanged || addedUserMessage) {
      shouldFollowRef.current = true;
    }

    // Scroll only the message viewport, not the page or its other ancestors.
    if (shouldFollowRef.current) {
      container.scrollTop = container.scrollHeight;
    }

    previousStateRef.current = {
      conversationId,
      messageCount: messages.length,
    };
  }, [conversationId, loading, messages]);

  return { scrollContainerRef, handleScroll };
}
