import { useCallback } from "react";
import {
  createTag,
  deleteTag,
  setConversationTags,
  updateTag,
} from "../lib/tagsApi";

export default function useConversationTagActions({
  conversationSearch,
  refreshConversations,
  refreshTags,
  selectedFolderId,
  selectedProjectId,
  selectedTagId,
  selectedWorkspaceId,
  setSelectedConversationIds,
  setSelectedTagId,
  setToast,
  showArchivedConversations,
  showTrashConversations,
  startNewChat,
  t,
}) {
  const refreshFilteredConversations = useCallback(
    async (tagId = selectedTagId) => {
      await refreshConversations(
        showArchivedConversations,
        selectedFolderId,
        selectedWorkspaceId,
        selectedProjectId,
        conversationSearch,
        showTrashConversations,
        tagId
      );
    },
    [
      conversationSearch,
      refreshConversations,
      selectedFolderId,
      selectedProjectId,
      selectedTagId,
      selectedWorkspaceId,
      showArchivedConversations,
      showTrashConversations,
    ]
  );

  const handleCreateTag = useCallback(async () => {
    const name = window.prompt(t("sidebar.tagCreatePrompt"));
    if (!name?.trim()) return;
    try {
      const tag = await createTag(name.trim());
      await refreshTags();
      setSelectedTagId(tag.id);
      await refreshFilteredConversations(tag.id);
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.tagCreateError"),
        type: "error",
      });
    }
  }, [refreshFilteredConversations, refreshTags, setSelectedTagId, setToast, t]);

  const handleRenameTag = useCallback(
    async (id, currentName, currentColor) => {
      const name = window.prompt(t("sidebar.tagRenamePrompt"), currentName);
      if (!name?.trim()) return;
      try {
        await updateTag(id, name.trim(), currentColor);
        await refreshTags();
      } catch (err) {
        setToast({
          message: err?.response?.data?.detail || t("app.tagRenameError"),
          type: "error",
        });
      }
    },
    [refreshTags, setToast, t]
  );

  const handleDeleteTag = useCallback(
    async (id, name) => {
      if (!window.confirm(t("sidebar.tagDeleteConfirm", { name }))) return;
      const wasSelected = id === selectedTagId;
      try {
        await deleteTag(id);
        if (wasSelected) setSelectedTagId(null);
        await refreshTags();
        await refreshFilteredConversations(wasSelected ? null : selectedTagId);
      } catch (err) {
        setToast({
          message: err?.response?.data?.detail || t("app.tagDeleteError"),
          type: "error",
        });
      }
    },
    [
      refreshFilteredConversations,
      refreshTags,
      selectedTagId,
      setSelectedTagId,
      setToast,
      t,
    ]
  );

  const handleSelectTag = useCallback(
    async (id) => {
      const tagId = id === null || id === undefined ? null : Number(id);
      setSelectedTagId(tagId);
      setSelectedConversationIds([]);
      startNewChat();
      await refreshFilteredConversations(tagId);
    },
    [
      refreshFilteredConversations,
      setSelectedConversationIds,
      setSelectedTagId,
      startNewChat,
    ]
  );

  const handleSetConversationTags = useCallback(
    async (id, tagIds) => {
      try {
        await setConversationTags(id, tagIds);
        await refreshFilteredConversations();
      } catch (err) {
        setToast({
          message:
            err?.response?.data?.detail || t("app.conversationTagError"),
          type: "error",
        });
      }
    },
    [refreshFilteredConversations, setToast, t]
  );

  return {
    handleCreateTag,
    handleRenameTag,
    handleDeleteTag,
    handleSelectTag,
    handleSetConversationTags,
  };
}
