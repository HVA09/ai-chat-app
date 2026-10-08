import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useTagManagement from "./useTagManagement";

describe("useTagManagement", () => {
  it("selects a tag, clears selections, starts a fresh chat, and refreshes", async () => {
    const refreshConversations = vi.fn().mockResolvedValue([]);
    const setSelectedTagId = vi.fn();
    const setSelectedConversationIds = vi.fn();
    const startNewChat = vi.fn();
    const { result } = renderHook(() => useTagManagement({
      t: (key) => key,
      selectedTagId: null,
      setSelectedTagId,
      setTags: vi.fn(),
      setSelectedConversationIds,
      startNewChat,
      refreshConversations,
      showArchivedConversations: false,
      selectedFolderId: null,
      selectedWorkspaceId: 2,
      selectedProjectId: null,
      conversationSearch: "",
      showTrashConversations: false,
      setToast: vi.fn(),
    }));
    await result.current.handleSelectTag("7");
    expect(setSelectedTagId).toHaveBeenCalledWith(7);
    expect(setSelectedConversationIds).toHaveBeenCalledWith([]);
    expect(startNewChat).toHaveBeenCalled();
    expect(refreshConversations).toHaveBeenCalledWith(false, null, 2, null, "", false, 7);
  });
});
