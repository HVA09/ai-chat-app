import { useCallback } from "react";
import { createConversationShare } from "../lib/sharedConversationsApi";

export default function useConversationSharing({
  conversationId,
  loading,
  messages,
  setShowShareManager,
  setToast,
  t,
}) {
  const handleShareConversation = useCallback(async () => {
    if (!conversationId) return;
    try {
      const protect = window.confirm(t("sharing.protectConfirm"));
      let password = null;

      if (protect) {
        password = window.prompt(t("sharing.passwordPrompt"));
        if (password === null) return;
        password = password.trim();
        if (password.length < 8) {
          setToast({ message: t("sharing.passwordTooShort"), type: "error" });
          return;
        }
      }

      const share = await createConversationShare(conversationId, 7, password);
      if (navigator.share) {
        try {
          await navigator.share({
            title: messages[0]?.text || t("appName"),
            url: share.url,
          });
          setToast({ message: t("sharing.sharedSuccess"), type: "success" });
          return;
        } catch (err) {
          if (err?.name === "AbortError") return;
        }
      }

      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(share.url);
        setToast({ message: t("sharing.linkCopied"), type: "success" });
        return;
      }

      window.prompt(t("sharing.copyPrompt"), share.url);
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("sharing.createError"),
        type: "error",
      });
    }
  }, [conversationId, messages, setToast, t]);

  const handleManageConversationShares = useCallback(() => {
    if (!conversationId || loading) return;
    setShowShareManager(true);
  }, [conversationId, loading, setShowShareManager]);

  return {
    handleManageConversationShares,
    handleShareConversation,
  };
}
