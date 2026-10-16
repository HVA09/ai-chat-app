import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { listBookmarkedMessages, toggleMessageBookmark } from "../lib/bookmarksApi";
import { getErrorMessage } from "../lib/errors";

/**
 * Owns bookmark state and actions for the active authenticated session.
 *
 * The hook intentionally receives message state and conversation actions from
 * App so bookmark behavior stays unchanged while the domain logic moves out
 * of the root component.
 */
export default function useBookmarks({
  authed,
  conversationId,
  loading,
  readOnlyConversation,
  setMessages,
  setToast,
  openConversation,
}) {
  const { t } = useTranslation();
  const [bookmarkedMessages, setBookmarkedMessages] = useState([]);
  const refreshRequestRef = useRef(0);
  const sessionVersionRef = useRef(0);
  const conversationIdRef = useRef(conversationId);
  conversationIdRef.current = conversationId;

  const refreshBookmarkedMessages = useCallback(async () => {
    const requestId = ++refreshRequestRef.current;
    const sessionVersion = sessionVersionRef.current;

    try {
      const nextBookmarks = await listBookmarkedMessages();
      if (
        sessionVersion !== sessionVersionRef.current ||
        requestId !== refreshRequestRef.current
      ) {
        return;
      }
      setBookmarkedMessages(nextBookmarks);
    } catch (err) {
      if (
        sessionVersion !== sessionVersionRef.current ||
        requestId !== refreshRequestRef.current
      ) {
        return;
      }
      setToast({
        message: getErrorMessage(err, t("app.bookmarksLoadError")),
        type: "error",
      });
    }
  }, [setToast, t]);

  const handleToggleMessageBookmark = useCallback(
    async (index) => {
      const requestedConversationId = conversationId;
      const sessionVersion = sessionVersionRef.current;

      if (!requestedConversationId || loading || readOnlyConversation) return;

      try {
        const result = await toggleMessageBookmark(
          requestedConversationId,
          index + 1
        );
        if (sessionVersion !== sessionVersionRef.current) return;

        // A slow request for an old conversation must not mutate the new
        // conversation's messages by index.
        if (conversationIdRef.current === requestedConversationId) {
          setMessages((prev) =>
            prev.map((message, messageIndex) =>
              messageIndex === index
                ? { ...message, isBookmarked: result.bookmarked }
                : message
            )
          );
        }
        await refreshBookmarkedMessages();
      } catch (err) {
        if (
          sessionVersion !== sessionVersionRef.current ||
          conversationIdRef.current !== requestedConversationId
        ) {
          return;
        }
        setToast({
          message: getErrorMessage(err, t("app.bookmarkError")),
          type: "error",
        });
      }
    },
    [
      conversationId,
      loading,
      readOnlyConversation,
      refreshBookmarkedMessages,
      setMessages,
      setToast,
      t,
    ]
  );

  const handleOpenBookmarkedMessage = useCallback(
    async (item) => {
      await openConversation(item.conversation_id);
    },
    [openConversation]
  );

  const resetBookmarks = useCallback(() => {
    // Invalidate pending reads and writes before clearing user-scoped data.
    sessionVersionRef.current += 1;
    refreshRequestRef.current += 1;
    setBookmarkedMessages([]);
  }, []);

  useEffect(() => {
    if (authed) {
      refreshBookmarkedMessages();
    } else {
      resetBookmarks();
    }
  }, [authed, refreshBookmarkedMessages, resetBookmarks]);

  return {
    bookmarkedMessages,
    refreshBookmarkedMessages,
    handleToggleMessageBookmark,
    handleOpenBookmarkedMessage,
    resetBookmarks,
  };
}
