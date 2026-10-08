import { renderHook, act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useConversationTags from "./useConversationTags";

vi.mock("../lib/tagsApi", () => ({
  listTags: vi.fn(),
  createTag: vi.fn(),
  updateTag: vi.fn(),
  deleteTag: vi.fn(),
  setConversationTags: vi.fn(),
}));

import { listTags, createTag, updateTag, deleteTag, setConversationTags } from "../lib/tagsApi";

describe("useConversationTags", () => {
  const refreshConversations = vi.fn().mockResolvedValue(undefined);
  const setToast = vi.fn();
  const startNewChat = vi.fn();
  const setSelectedConversationIds = vi.fn();
  const setTags = vi.fn();
  const setSelectedTagId = vi.fn();
  const props = {
    showArchivedConversations: false,
    showTrashConversations: false,
    selectedFolderId: null,
    selectedWorkspaceId: 7,
    selectedProjectId: null,
    conversationSearch: "",
    refreshConversations,
    setSelectedConversationIds,
    startNewChat,
    setToast,
    t: (key) => key,
    tags: [],
    setTags,
    selectedTagId: null,
    setSelectedTagId,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    listTags.mockResolvedValue([{ id: 1, name: "Work" }]);
    createTag.mockResolvedValue({ id: 2, name: "New" });
    updateTag.mockResolvedValue({});
    deleteTag.mockResolvedValue({});
    setConversationTags.mockResolvedValue({});
    vi.stubGlobal("prompt", vi.fn(() => "New"));
    vi.stubGlobal("confirm", vi.fn(() => true));
  });

  it("refreshes tags and creates a tag with the current filter", async () => {
    const { result } = renderHook(() => useConversationTags(props));
    await act(async () => { await result.current.refreshTags(); });
    expect(setTags).toHaveBeenCalledWith([{ id: 1, name: "Work" }]);
    await act(async () => { await result.current.handleCreateTag(); });
    expect(createTag).toHaveBeenCalledWith("New");
    expect(setSelectedTagId).toHaveBeenCalledWith(2);
    expect(refreshConversations).toHaveBeenLastCalledWith(false, null, 7, null, "", false, 2);
  });

  it("selects a tag, clears conversation selection, and starts a new chat", async () => {
    const { result } = renderHook(() => useConversationTags(props));
    await act(async () => { await result.current.handleSelectTag("3"); });
    expect(setSelectedTagId).toHaveBeenCalledWith(3);
    expect(setSelectedConversationIds).toHaveBeenCalledWith([]);
    expect(startNewChat).toHaveBeenCalled();
    expect(refreshConversations).toHaveBeenLastCalledWith(false, null, 7, null, "", false, 3);
  });

  it("updates conversation tags using the selected filter", async () => {
    const { result } = renderHook(() => useConversationTags({...props, selectedTagId: 5}));
    await act(async () => { await result.current.handleSetConversationTags(42, [5]); });
    expect(setConversationTags).toHaveBeenCalledWith(42, [5]);
    expect(refreshConversations).toHaveBeenLastCalledWith(false, null, 7, null, "", false, 5);
  });

  it("deletes the selected tag and clears the filter", async () => {
    const { result } = renderHook(() => useConversationTags({...props, selectedTagId: 4}));
    await act(async () => { await result.current.handleDeleteTag(4, "Work"); });
    expect(deleteTag).toHaveBeenCalledWith(4);
    expect(setSelectedTagId).toHaveBeenCalledWith(null);
    expect(refreshConversations).toHaveBeenLastCalledWith(false, null, 7, null, "", false, null);
  });
});
