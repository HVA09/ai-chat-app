import { useCallback } from "react";
import { exportConversation } from "../lib/conversationsApi";

export default function useConversationExport({
  conversationId,
  loading,
  setToast,
  t,
}) {
  const handleExportConversation = useCallback(
    async (format = "markdown") => {
      if (!conversationId || loading) return;

      try {
        await exportConversation(conversationId, format);
        setToast({ message: t("exportConversationSuccess"), type: "success" });
      } catch (err) {
        setToast({
          message: err?.response?.data?.detail || t("exportConversationError"),
          type: "error",
        });
      }
    },
    [conversationId, loading, setToast, t]
  );

  return { handleExportConversation };
}
