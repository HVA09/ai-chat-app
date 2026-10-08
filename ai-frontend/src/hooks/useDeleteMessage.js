import { useCallback } from "react";
import { getConversation } from "../lib/conversationsApi";
import api from "../lib/api";

export default function useDeleteMessage({
  conversationId,
  loading,
  editingMessageIndex,
  readOnlyConversation,
  setError,
  setMessages,
  refreshConversations,
  getWelcomeMessage,
  t,
  setToast,
}) {
  const deleteMessage = useCallback(async (index) => {
    if (
      !conversationId ||
      loading ||
      editingMessageIndex !== null ||
      readOnlyConversation
    ) {
      return;
    }

    const isArabic = document.documentElement.lang === "ar";
    const confirmed = window.confirm(
      isArabic
        ? "حذف هذه الرسالة؟ إذا كانت رسالة مستخدم فسيُحذف رد المساعد المرتبط بها أيضًا."
        : "Delete this message? For a user message, its linked assistant reply will also be deleted."
    );
    if (!confirmed) return;

    setError("");
    try {
      await api.delete(`/chat/${conversationId}/messages/${index + 1}`);
      const data = await getConversation(conversationId);
      setMessages(
        data.messages.length
          ? data.messages.map((message) => ({
              role: message.role,
              text: message.content,
              time: new Date(message.created_at).toLocaleTimeString(),
              sources: message.sources ?? [],
            }))
          : [getWelcomeMessage(t)]
      );
      await refreshConversations();
    } catch (err) {
      if (err?.response?.status === 401) return;
      setToast({
        message:
          err?.response?.data?.detail ||
          (isArabic ? "تعذر حذف الرسالة" : "Couldn't delete the message"),
        type: "error",
      });
    }
  }, [
    conversationId,
    editingMessageIndex,
    getWelcomeMessage,
    loading,
    readOnlyConversation,
    refreshConversations,
    setError,
    setMessages,
    setToast,
    t,
  ]);

  return { deleteMessage };
}
