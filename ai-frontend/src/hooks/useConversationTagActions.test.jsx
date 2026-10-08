import { renderHook, act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/tagsApi", () => ({
  createTag: vi.fn(),
  deleteTag: vi.fn(),
  setConversationTags: vi.fn(),
  updateTag: vi.fn(),
}));

import {
  createTag,
  deleteTag,
  setConversationTags,
  updateTag,
} from "../lib/tagsApi";
import useConversationTagActions from "./useConversationTagActions";

describe("useConversationTagActions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.prompt = vi.fn();
    window.confirm = vi.fn(() => true);
  });

  function createProps(overrides = {}) {
    return {
      conversationSearch: "",
      refreshConversations: vi.fn(),
      refreshTags: vi.fn(),
      selectedFolderId: null,
      selectedProjectId: null,
      selectedTagId: null,
      selectedWorkspaceId: null,
      setSelectedConversationIds: vi.fn(),
      setSelectedTagId: vi.fn(),
      setToast: vi.fn(),
      showArchivedConversations: false,
      showTrashConversations: false,
      startNewChat: vi.fn(),
      t: vi.fn((key) => key),
      ...overrides,
    };
  }

  it("creates a tag and refreshes the filtered conversations", async () => {
    window.prompt.mockReturnValue(" Work ");
    createTag.mockResolvedValue({ id: 7 });
    const props = createProps();
    const { result } = renderHook(() => useConversationTagActions(props));

    await act(async () => result.current.handleCreateTag());

    expect(createTag).toHaveBeenCalledWith("Work");
    expect(props.refreshTags).toHaveBeenCalled();
    expect(props.setSelectedTagId).toHaveBeenCalledWith(7);
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false,
      null,
      null,
      null,
      "",
      false,
      7
    );
  });

  it("selects a tag by resetting the active chat first", async () => {
    const props = createProps();
    const { result } = renderHook(() => useConversationTagActions(props));

    await act(async () => result.current.handleSelectTag("12"));

    expect(props.setSelectedTagId).toHaveBeenCalledWith(12);
    expect(props.setSelectedConversationIds).toHaveBeenCalledWith([]);
    expect(props.startNewChat).toHaveBeenCalled();
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false,
      null,
      null,
      null,
      "",
      false,
      12
    );
  });

  it("deletes the selected tag and clears its filter", async () => {
    deleteTag.mockResolvedValue({});
    const props = createProps({ selectedTagId: 5 });
    const { result } = renderHook(() => useConversationTagActions(props));

    await act(async () => result.current.handleDeleteTag(5, "Work"));

    expect(deleteTag).toHaveBeenCalledWith(5);
    expect(props.setSelectedTagId).toHaveBeenCalledWith(null);
    expect(props.refreshTags).toHaveBeenCalled();
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false,
      null,
      null,
      null,
      "",
      false,
      null
    );
  });

  it("updates tags on a conversation and refreshes the current filter", async () => {
    setConversationTags.mockResolvedValue({});
    const props = createProps({ selectedTagId: 3 });
    const { result } = renderHook(() => useConversationTagActions(props));

    await act(async () => result.current.handleSetConversationTags(42, [1, 3]));

    expect(setConversationTags).toHaveBeenCalledWith(42, [1, 3]);
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false,
      null,
      null,
      null,
      "",
      false,
      3
    );
  });
});
