import { useCallback, useRef } from "react";
import { createTag, deleteTag, listTags, setConversationTags, updateTag } from "../lib/tagsApi";
import { getErrorMessage } from "../lib/errors";

export default function useTagManagement({
  tagRequestGenerationRef,
  t, selectedTagId, setSelectedTagId, setTags, setSelectedConversationIds,
  startNewChat, refreshConversations, showArchivedConversations, selectedFolderId,
  selectedWorkspaceId, selectedProjectId, conversationSearch, showTrashConversations, setToast,
}) {
  const refreshRequestRef = useRef(0);

  const refreshTags = useCallback(async () => {
    const requestId = ++refreshRequestRef.current;
    const resetGeneration = tagRequestGenerationRef?.current ?? 0;
    const isCurrentRequest = () =>
      requestId === refreshRequestRef.current &&
      resetGeneration === (tagRequestGenerationRef?.current ?? 0);

    try {
      const nextTags = await listTags();
      if (!isCurrentRequest()) return;
      setTags(nextTags);
    } catch (err) {
      // A stale failure should not surface after logout or a newer refresh.
      if (!isCurrentRequest()) return;
      setToast({
        message: getErrorMessage(err, t("app.tagsLoadError")),
        type: "error",
      });
    }
  }, [setTags, setToast, t, tagRequestGenerationRef]);

  const handleCreateTag = useCallback(async () => {
    const name = window.prompt(t("sidebar.tagCreatePrompt"));
    if (!name?.trim()) return;
    try {
      const tag = await createTag(name.trim());
      await refreshTags();
      setSelectedTagId(tag.id);
      await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId, selectedProjectId, conversationSearch, showTrashConversations, tag.id);
    } catch (err) {
      setToast({ message: err?.response?.data?.detail || t("app.tagCreateError"), type: "error" });
    }
  }, [conversationSearch, refreshConversations, refreshTags, selectedFolderId, selectedProjectId, selectedWorkspaceId, setSelectedTagId, setToast, showArchivedConversations, showTrashConversations, t]);

  const handleRenameTag = useCallback(async (id, currentName, currentColor) => {
    const name = window.prompt(t("sidebar.tagRenamePrompt"), currentName);
    if (!name?.trim()) return;
    try { await updateTag(id, name.trim(), currentColor); await refreshTags(); }
    catch (err) { setToast({ message: err?.response?.data?.detail || t("app.tagRenameError"), type: "error" }); }
  }, [refreshTags, setToast, t]);

  const handleDeleteTag = useCallback(async (id, name) => {
    if (!window.confirm(t("sidebar.tagDeleteConfirm", { name }))) return;
    const wasSelected = id === selectedTagId;
    try {
      await deleteTag(id);
      if (wasSelected) setSelectedTagId(null);
      await refreshTags();
      await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId, selectedProjectId, conversationSearch, showTrashConversations, wasSelected ? null : selectedTagId);
    } catch (err) {
      setToast({ message: err?.response?.data?.detail || t("app.tagDeleteError"), type: "error" });
    }
  }, [conversationSearch, refreshConversations, refreshTags, selectedFolderId, selectedProjectId, selectedTagId, selectedWorkspaceId, setSelectedTagId, setToast, showArchivedConversations, showTrashConversations, t]);

  const handleSelectTag = useCallback(async (id) => {
    const tagId = id === null || id === undefined ? null : Number(id);
    setSelectedTagId(tagId);
    setSelectedConversationIds([]);
    startNewChat();
    await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId, selectedProjectId, conversationSearch, showTrashConversations, tagId);
  }, [conversationSearch, refreshConversations, selectedFolderId, selectedProjectId, selectedWorkspaceId, setSelectedConversationIds, setSelectedTagId, showArchivedConversations, showTrashConversations, startNewChat]);

  const handleSetConversationTags = useCallback(async (id, tagIds) => {
    try {
      await setConversationTags(id, tagIds);
      await refreshConversations(showArchivedConversations, selectedFolderId, selectedWorkspaceId, selectedProjectId, conversationSearch, showTrashConversations, selectedTagId);
    } catch (err) {
      setToast({ message: err?.response?.data?.detail || t("app.conversationTagError"), type: "error" });
    }
  }, [conversationSearch, refreshConversations, selectedFolderId, selectedProjectId, selectedTagId, selectedWorkspaceId, setToast, showArchivedConversations, showTrashConversations, t]);

  return { refreshTags, handleCreateTag, handleRenameTag, handleDeleteTag, handleSelectTag, handleSetConversationTags };
}
