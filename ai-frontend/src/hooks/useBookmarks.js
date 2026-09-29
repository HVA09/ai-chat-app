import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { listBookmarkedMessages, toggleMessageBookmark } from "../lib/bookmarksApi";
import { getErrorMessage } from "../lib/errors";

export default function useBookmarks({ setToast, conversationId, loading, readOnlyConversation, setMessages, openConversation }) {
  const { t } = useTranslation();
  const [bookmarkedMessages, setBookmarkedMessages] = useState([]);

  const refreshBookmarkedMessages = useCallback(async () => {
    try {
      setBookmarkedMessages(await listBookmarkedMessages());
    } catch (err) {
      setToast({
        message: getErrorMessage(err, t("app.bookmarksLoadError")),
        type: "error",
      });
    }
  }, [setToast, t]);

  const handleToggleMessageBookmark = useCallback(async (index) => {
    if (!conversationId || loading || readOnlyConversation) return;

    try {
      const result = await toggleMessageBookmark(conversationId, index + 1);
      setMessages((prev) =>
        prev.map((message, messageIndex) =>
          messageIndex === index
            ? { ...message, isBookmarked: result.bookmarked }
            : message
        )
      );
      await refreshBookmarkedMessages();
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.bookmarkError"),
        type: "error",
      });
    }
  }, [conversationId, loading, readOnlyConversation, refreshBookmarkedMessages, setMessages, setToast, t]);

  const handleOpenBookmarkedMessage = useCallback(async (item) => {
    await openConversation(item.conversation_id);
  }, [openConversation]);

  return {
    bookmarkedMessages,
    refreshBookmarkedMessages,
    handleToggleMessageBookmark,
    handleOpenBookmarkedMessage,
  };
}
