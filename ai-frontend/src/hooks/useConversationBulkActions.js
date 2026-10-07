import { useCallback } from "react";
import {
  deleteConversation,
  exportConversations,
  moveConversationToFolder,
  toggleArchiveConversation,
  toggleTrashConversation,
} from "../lib/conversationsApi";

export default function useConversationBulkActions({
  conversationId,
  refreshConversations,
  selectedConversationIds,
  selectedFolderId,
  selectedProjectId,
  selectedWorkspaceId,
  setSelectedConversationIds,
  setToast,
  showArchivedConversations,
  showTrashConversations,
  startNewChat,
  t,
}) {
  const refreshCurrentConversations = useCallback(
    () =>
      refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId
      ),
    [
      refreshConversations,
      selectedFolderId,
      selectedProjectId,
      selectedWorkspaceId,
      showArchivedConversations,
    ]
  );

  const handleBulkArchive = useCallback(async () => {
    if (!selectedConversationIds.length) return;

    const results = await Promise.allSettled(
      selectedConversationIds.map((id) => toggleArchiveConversation(id))
    );
    const failed = results.filter((result) => result.status === "rejected").length;

    if (selectedConversationIds.includes(conversationId)) startNewChat();
    setSelectedConversationIds([]);
    await refreshCurrentConversations();

    if (failed) {
      setToast({
        message: t("app.bulkActionError", { count: failed }),
        type: "error",
      });
    }
  }, [
    conversationId,
    refreshCurrentConversations,
    selectedConversationIds,
    setSelectedConversationIds,
    setToast,
    startNewChat,
    t,
  ]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedConversationIds.length) return;

    const confirmed = window.confirm(
      t("sidebar.bulkDeleteConfirm", { count: selectedConversationIds.length })
    );
    if (!confirmed) return;

    const selectedIds = [...selectedConversationIds];
    const action = showTrashConversations
      ? deleteConversation
      : toggleTrashConversation;

    const results = await Promise.allSettled(selectedIds.map((id) => action(id)));
    const failed = results.filter((result) => result.status === "rejected").length;

    if (selectedIds.includes(conversationId)) startNewChat();
    setSelectedConversationIds([]);
    await refreshCurrentConversations();

    if (failed) {
      setToast({
        message: t("app.bulkActionError", { count: failed }),
        type: "error",
      });
    }
  }, [
    conversationId,
    refreshCurrentConversations,
    selectedConversationIds,
    setSelectedConversationIds,
    setToast,
    showTrashConversations,
    startNewChat,
    t,
  ]);

  const handleBulkExport = useCallback(async () => {
    if (!selectedConversationIds.length) return;

    try {
      await exportConversations(selectedConversationIds);
      setSelectedConversationIds([]);
      setToast({ message: t("app.bulkExportSuccess"), type: "success" });
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.bulkExportError"),
        type: "error",
      });
    }
  }, [selectedConversationIds, setSelectedConversationIds, setToast, t]);

  const handleBulkMoveToFolder = useCallback(
    async (folderValue) => {
      if (!selectedConversationIds.length || folderValue === "") return;

      const folderId = folderValue === "__none__" ? null : Number(folderValue);
      const selectedIds = [...selectedConversationIds];
      const results = await Promise.allSettled(
        selectedIds.map((id) => moveConversationToFolder(id, folderId))
      );
      const failed = results.filter(
        (result) => result.status === "rejected"
      ).length;

      if (selectedIds.includes(conversationId) && folderId !== selectedFolderId) {
        startNewChat();
      }
      setSelectedConversationIds([]);
      await refreshCurrentConversations();

      if (failed) {
        setToast({
          message: t("app.bulkActionError", { count: failed }),
          type: "error",
        });
      }
    },
    [
      conversationId,
      refreshCurrentConversations,
      selectedConversationIds,
      selectedFolderId,
      setSelectedConversationIds,
      setToast,
      startNewChat,
      t,
    ]
  );

  return {
    handleBulkArchive,
    handleBulkDelete,
    handleBulkExport,
    handleBulkMoveToFolder,
  };
}
