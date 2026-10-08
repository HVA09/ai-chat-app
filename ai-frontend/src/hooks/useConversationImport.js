import { useCallback } from "react";
import {
  importConversation,
  importConversations,
} from "../lib/conversationsApi";

export default function useConversationImport({
  selectedWorkspaceId,
  t,
  setToast,
  setShowArchivedConversations,
  setShowTrashConversations,
  setConversationSearch,
  setSelectedTagId,
  setSelectedFolderId,
  setSelectedProjectId,
  setSelectedConversationIds,
  refreshConversations,
  openConversation,
}) {
  const handleImportConversation = useCallback(
    async (file) => {
      if (!file) return;

      if (file.size > 10 * 1024 * 1024) {
        setToast({ message: t("importConversationTooLarge"), type: "error" });
        return;
      }

      if (selectedWorkspaceId === null || selectedWorkspaceId === undefined) {
        setToast({ message: t("importConversationError"), type: "error" });
        return;
      }

      try {
        const text = await file.text();
        let payload;
        try {
          payload = JSON.parse(text);
        } catch {
          setToast({ message: t("importConversationInvalidFile"), type: "error" });
          return;
        }

        if (
          payload &&
          typeof payload === "object" &&
          Array.isArray(payload.conversations)
        ) {
          if (payload.version !== 1 || payload.conversations.length === 0) {
            setToast({ message: t("importConversationInvalidFile"), type: "error" });
            return;
          }

          const imported = await importConversations(selectedWorkspaceId, payload);
          setShowArchivedConversations(false);
          setShowTrashConversations(false);
          setConversationSearch("");
          setSelectedTagId(null);
          setSelectedFolderId(null);
          setSelectedProjectId(null);
          setSelectedConversationIds([]);

          await refreshConversations(
            false,
            null,
            selectedWorkspaceId,
            null,
            "",
            false,
            null
          );

          const firstId = imported.conversation_ids?.[0];
          if (firstId) {
            await openConversation(firstId);
          }

          setToast({
            message: t("bulkImportSuccess", { count: imported.imported_count }),
            type: "success",
          });
          return;
        }

        if (
          !payload ||
          typeof payload !== "object" ||
          !Array.isArray(payload.messages) ||
          payload.messages.length === 0
        ) {
          setToast({ message: t("importConversationInvalidFile"), type: "error" });
          return;
        }

        const imported = await importConversation(selectedWorkspaceId, {
          title: payload.title || "Imported conversation",
          messages: payload.messages,
          folder_id: payload.folder_id ?? null,
          project_id: payload.project_id ?? null,
          assistant_id: payload.assistant_id ?? null,
          ai_model: payload.ai_model ?? null,
        });

        setShowArchivedConversations(false);
        setShowTrashConversations(false);
        setConversationSearch("");
        setSelectedTagId(null);
        setSelectedFolderId(imported.folder_id ?? null);
        setSelectedProjectId(imported.project_id ?? null);

        await refreshConversations(
          false,
          imported.folder_id ?? null,
          selectedWorkspaceId,
          imported.project_id ?? null,
          "",
          false,
          null
        );
        await openConversation(imported.id);
        setToast({ message: t("importConversationSuccess"), type: "success" });
      } catch (err) {
        setToast({
          message: err?.response?.data?.detail || t("importConversationError"),
          type: "error",
        });
      }
    },
    [
      openConversation,
      refreshConversations,
      selectedWorkspaceId,
      setConversationSearch,
      setSelectedConversationIds,
      setSelectedFolderId,
      setSelectedProjectId,
      setSelectedTagId,
      setShowArchivedConversations,
      setShowTrashConversations,
      setToast,
      t,
    ]
  );

  return { handleImportConversation };
}
