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

vi.mock("../lib/errors", () => ({
  getErrorMessage: vi.fn((error, fallback) => error?.message || fallback),
}));

import { listTags, createTag, updateTag, deleteTag, setConversationTags } from "../lib/tagsApi";

describe("useConversationTags", () => {
  const refreshConversations = vi.fn().mockResolvedValue(undefined);
  const setToast = vi.fn();
  const startNewChat = vi.fn();
  const setSelectedConversationIds = vi.fn();
  const setTags = vi.fn();
  const baseProps = {
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
    setSelectedTagId: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    listTags.mockResolvedValue([{ id: 1, name: "Work" }]);
    createTag.mockResolvedValue({ id: 2, name: "New" });
    updateTag.mockResolvedValue({});
    deleteTag.mockResolvedValue({});
    setConversationTags.mockResolvedValue({});
  });

  it("loads tags and creates a tag while refreshing the active filter", async () => {
    const { result } = renderHook(() => useConversationTags(baseProps));
    await act(async () => { await result.current.refreshTags(); });
    expect(result.current.tags).toEqual([{ id: 1, name: "Work" }]);

    vi.stubGlobal("prompt", vi.fn(() => "New"));
    await act(async () => { await result.current.handleCreateTag(); });

    expect(createTag).toHaveBeenCalledWith("New");
    expect(result.current.selectedTagId).toBe(2);
    expect(refreshConversations).toHaveBeenLastCalledWith(false, null, 7, null, "", false, 2);
  });

  it("selects a tag, clears selection, and starts a new chat", async () => {
    const { result } = renderHook(() => useConversationTags(baseProps));
    await act(async () => { await result.current.handleSelectTag("3"); });

    expect(result.current.selectedTagId).toBe(3);
    expect(setSelectedConversationIds).toHaveBeenCalledWith([]);
    expect(startNewChat).toHaveBeenCalled();
    expect(refreshConversations).toHaveBeenLastCalledWith(false, null, 7, null, "", false, 3);
  });

  it("updates conversation tags and refreshes the selected tag filter", async () => {
    const { result } = renderHook(() => useConversationTags(baseProps));
    await act(async () => { await result.current.handleSelectTag(5); });
    await act(async () => { await result.current.handleSetConversationTags(42, [5]); });

    expect(setConversationTags).toHaveBeenCalledWith(42, [5]);
    expect(refreshConversations).toHaveBeenLastCalledWith(false, null, 7, null, "", false, 5);
  });

  it("deletes a selected tag and clears its filter", async () => {
    vi.stubGlobal("confirm", vi.fn(() => true));
    const { result } = renderHook(() => useConversationTags(baseProps));
    await act(async () => { await result.current.handleSelectTag(4); });
    await act(async () => { await result.current.handleDeleteTag(4, "Work"); });

    expect(deleteTag).toHaveBeenCalledWith(4);
    expect(result.current.selectedTagId).toBe(null);
    expect(refreshConversations).toHaveBeenLastCalledWith(false, null, 7, null, "", false, null);
  });
});
