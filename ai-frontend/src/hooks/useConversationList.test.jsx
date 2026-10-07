import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useConversationList from "./useConversationList";
import { listConversations } from "../lib/conversationsApi";

vi.mock("../lib/conversationsApi", () => ({
  listConversations: vi.fn(),
}));

describe("useConversationList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function createProps() {
    return {
      filters: {
        showArchivedConversations: false,
        showTrashConversations: false,
        selectedFolderId: null,
        selectedWorkspaceId: 2,
        selectedProjectId: 3,
        selectedTagId: null,
        conversationSearch: "",
      },
      setToast: vi.fn(),
      t: (key) => key,
    };
  }

  it("loads and paginates conversations", async () => {
    listConversations
      .mockResolvedValueOnce([
        { id: 1 },
        { id: 2 },
      ])
      .mockResolvedValueOnce([
        { id: 3 },
        { id: 4 },
        { id: 5 },
      ]);

    const { result } = renderHook(() => useConversationList(createProps()));

    await act(async () => {
      await result.current.refreshConversations();
    });

    expect(listConversations).toHaveBeenLastCalledWith(
      false,
      null,
      2,
      3,
      "",
      false,
      null,
      0,
      51
    );
    expect(result.current.conversations).toEqual([{ id: 1 }, { id: 2 }]);

    act(() => {
      result.current.loadMoreConversations();
    });

    await act(async () => {
      await result.current.loadMoreConversations();
    });

    expect(result.current.conversations).toEqual([
      { id: 1 },
      { id: 2 },
      { id: 3 },
      { id: 4 },
      { id: 5 },
    ]);
  });

  it("resets its state and invalidates pending loads", async () => {
    listConversations.mockImplementation(() => new Promise(() => {}));

    const { result } = renderHook(() => useConversationList(createProps()));

    act(() => {
      result.current.refreshConversations();
      result.current.resetConversations();
    });

    expect(result.current.conversations).toEqual([]);
    expect(result.current.hasMoreConversations).toBe(false);
    expect(result.current.conversationsLoading).toBe(false);
    expect(result.current.conversationsLoadingMore).toBe(false);
  });
});
