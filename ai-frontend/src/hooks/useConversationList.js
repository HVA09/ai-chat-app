import { useCallback, useRef, useState } from "react";
import { listConversations } from "../lib/conversationsApi";
import { getErrorMessage } from "../lib/errors";

const PAGE_SIZE = 50;

export default function useConversationList({
  filters,
  setToast,
  t,
}) {
  const [conversations, setConversations] = useState([]);
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [conversationsLoadingMore, setConversationsLoadingMore] = useState(false);
  const [hasMoreConversations, setHasMoreConversations] = useState(false);
  const conversationLoadRequestRef = useRef(0);

  const refreshConversations = useCallback(
    async (
      includeArchived = filters.showArchivedConversations,
      folderId = filters.selectedFolderId,
      workspaceId = filters.selectedWorkspaceId,
      projectId = filters.selectedProjectId,
      search = filters.conversationSearch,
      includeDeleted = filters.showTrashConversations,
      tagId = filters.selectedTagId,
      reset = true
    ) => {
      if (reset) setConversationsLoading(true);
      else setConversationsLoadingMore(true);

      const requestId = ++conversationLoadRequestRef.current;
      try {
        const list = await listConversations(
          includeArchived,
          folderId,
          workspaceId,
          projectId,
          search,
          includeDeleted,
          tagId,
          reset ? 0 : conversations.length,
          PAGE_SIZE + 1
        );
        const page = list.slice(0, PAGE_SIZE);

        if (requestId !== conversationLoadRequestRef.current) return;

        if (reset) {
          setConversations(page);
        } else {
          setConversations((current) => {
            const existingIds = new Set(current.map((item) => item.id));
            return [...current, ...page.filter((item) => !existingIds.has(item.id))];
          });
        }

        setHasMoreConversations(list.length > PAGE_SIZE);
      } catch (err) {
        setToast({
          message: getErrorMessage(err, t("app.conversationsLoadError")),
          type: "error",
        });
      } finally {
        if (reset) setConversationsLoading(false);
        else setConversationsLoadingMore(false);
      }
    },
    [
      conversations.length,
      filters.conversationSearch,
      filters.selectedFolderId,
      filters.selectedTagId,
      filters.selectedWorkspaceId,
      filters.showArchivedConversations,
      filters.showTrashConversations,
      setToast,
      t,
    ]
  );

  const loadMoreConversations = useCallback(async () => {
    if (!hasMoreConversations || conversationsLoading || conversationsLoadingMore) return;

    await refreshConversations(
      filters.showArchivedConversations,
      filters.selectedFolderId,
      filters.selectedWorkspaceId,
      filters.selectedProjectId,
      filters.conversationSearch,
      filters.showTrashConversations,
      filters.selectedTagId,
      false
    );
  }, [
    conversationsLoading,
    conversationsLoadingMore,
    filters.conversationSearch,
    filters.selectedFolderId,
    filters.selectedProjectId,
    filters.selectedTagId,
    filters.selectedWorkspaceId,
    filters.showArchivedConversations,
    filters.showTrashConversations,
    hasMoreConversations,
    refreshConversations,
  ]);

  const resetConversations = useCallback(() => {
    conversationLoadRequestRef.current += 1;
    setConversations([]);
    setHasMoreConversations(false);
    setConversationsLoading(false);
    setConversationsLoadingMore(false);
  }, []);

  return {
    conversations,
    conversationsLoading,
    conversationsLoadingMore,
    hasMoreConversations,
    refreshConversations,
    loadMoreConversations,
    resetConversations,
  };
}
