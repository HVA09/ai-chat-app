import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import useTags from "./useTags";

const apiMocks = vi.hoisted(() => ({
  listTags: vi.fn(),
  createTag: vi.fn(),
  updateTag: vi.fn(),
  deleteTag: vi.fn(),
  setConversationTags: vi.fn(),
}));

vi.mock("../lib/tagsApi", () => apiMocks);
vi.mock("../lib/errors", () => ({
  getErrorMessage: vi.fn((_err, fallback) => fallback),
}));

function createProps(overrides = {}) {
  return {
    t: (key) => key,
    selectedTagId: 7,
    showArchivedConversations: false,
    showTrashConversations: false,
    selectedFolderId: 2,
    selectedWorkspaceId: 3,
    selectedProjectId: 4,
    conversationSearch: "hello",
    setTags: vi.fn(),
    setSelectedTagId: vi.fn(),
    setSelectedConversationIds: vi.fn(),
    startNewChat: vi.fn(),
    refreshConversations: vi.fn(),
    setToast: vi.fn(),
    ...overrides,
  };
}

describe("useTags", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.listTags.mockResolvedValue([{ id: 7, name: "Work" }]);
    apiMocks.createTag.mockResolvedValue({ id: 9, name: "New" });
    apiMocks.updateTag.mockResolvedValue({});
    apiMocks.deleteTag.mockResolvedValue({});
    apiMocks.setConversationTags.mockResolvedValue({});
    window.prompt = vi.fn();
    window.confirm = vi.fn(() => true);
  });

  it("refreshes tags and reports load errors", async () => {
    const props = createProps();
    const { result } = renderHook(() => useTags(props));

    await act(async () => {
      await result.current.refreshTags();
    });

    expect(apiMocks.listTags).toHaveBeenCalled();
    expect(props.setTags).toHaveBeenCalledWith([{ id: 7, name: "Work" }]);
  });

  it("selects a tag, resets the chat, and refreshes conversations", async () => {
    const props = createProps();
    const { result } = renderHook(() => useTags(props));

    await act(async () => {
      await result.current.handleSelectTag("9");
    });

    expect(props.setSelectedTagId).toHaveBeenCalledWith(9);
    expect(props.setSelectedConversationIds).toHaveBeenCalledWith([]);
    expect(props.startNewChat).toHaveBeenCalled();
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false, 2, 3, 4, "hello", false, 9
    );
  });

  it("creates a tag and selects it", async () => {
    window.prompt.mockReturnValue("  New tag  ");
    const props = createProps();
    const { result } = renderHook(() => useTags(props));

    await act(async () => {
      await result.current.handleCreateTag();
    });

    expect(apiMocks.createTag).toHaveBeenCalledWith("New tag");
    expect(props.setSelectedTagId).toHaveBeenCalledWith(9);
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false, 2, 3, 4, "hello", false, 9
    );
  });

  it("sets conversation tags and refreshes the filtered list", async () => {
    const props = createProps();
    const { result } = renderHook(() => useTags(props));

    await act(async () => {
      await result.current.handleSetConversationTags(15, [1, 4]);
    });

    expect(apiMocks.setConversationTags).toHaveBeenCalledWith(15, [1, 4]);
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false, 2, 3, 4, "hello", false, 7
    );
  });
});
