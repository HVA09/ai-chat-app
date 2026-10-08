import { renderHook, act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as tagsApi from "../lib/tagsApi";
import useConversationTags from "./useConversationTags";

vi.mock("../lib/tagsApi", () => ({
  listTags: vi.fn(),
  createTag: vi.fn(),
  updateTag: vi.fn(),
  deleteTag: vi.fn(),
  setConversationTags: vi.fn(),
}));

describe("useConversationTags", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "prompt").mockRestore?.();
    vi.spyOn(window, "confirm").mockRestore?.();
  });

  function createProps(overrides = {}) {
    return {
      tags: [],
      setTags: vi.fn(),
      selectedTagId: null,
      setSelectedTagId: vi.fn(),
      setSelectedConversationIds: vi.fn(),
      showArchivedConversations: false,
      selectedFolderId: null,
      selectedWorkspaceId: 4,
      selectedProjectId: null,
      conversationSearch: "",
      showTrashConversations: false,
      refreshConversations: vi.fn(),
      startNewChat: vi.fn(),
      setToast: vi.fn(),
      t: (key) => key,
      ...overrides,
    };
  }

  it("refreshes tags and creates a tag with the current conversation filter", async () => {
    const props = createProps();
    vi.mocked(tagsApi.listTags).mockResolvedValue([{ id: 7, name: "Work" }]);
    vi.mocked(tagsApi.createTag).mockResolvedValue({ id: 9, name: "Urgent" });
    vi.spyOn(window, "prompt").mockReturnValue("Urgent");

    const { result } = renderHook(() => useConversationTags(props));

    await act(async () => result.current.refreshTags());
    expect(props.setTags).toHaveBeenCalledWith([{ id: 7, name: "Work" }]);

    await act(async () => result.current.handleCreateTag());
    expect(tagsApi.createTag).toHaveBeenCalledWith("Urgent");
    expect(props.setSelectedTagId).toHaveBeenCalledWith(9);
    expect(props.refreshConversations).toHaveBeenLastCalledWith(
      false,
      null,
      4,
      null,
      "",
      false,
      9
    );
  });

  it("selects a tag after starting a fresh chat and clearing selection", async () => {
    const props = createProps();

    const { result } = renderHook(() => useConversationTags(props));

    await act(async () => result.current.handleSelectTag("12"));

    expect(props.setSelectedTagId).toHaveBeenCalledWith(12);
    expect(props.setSelectedConversationIds).toHaveBeenCalledWith([]);
    expect(props.startNewChat).toHaveBeenCalled();
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false,
      null,
      4,
      null,
      "",
      false,
      12
    );
  });
});
