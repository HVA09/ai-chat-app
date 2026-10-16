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
        { id: 3 },
        { id: 4 },
        { id: 5 },
        { id: 6 },
        { id: 7 },
        { id: 8 },
        { id: 9 },
        { id: 10 },
        { id: 11 },
        { id: 12 },
        { id: 13 },
        { id: 14 },
        { id: 15 },
        { id: 16 },
        { id: 17 },
        { id: 18 },
        { id: 19 },
        { id: 20 },
        { id: 21 },
        { id: 22 },
        { id: 23 },
        { id: 24 },
        { id: 25 },
        { id: 26 },
        { id: 27 },
        { id: 28 },
        { id: 29 },
        { id: 30 },
        { id: 31 },
        { id: 32 },
        { id: 33 },
        { id: 34 },
        { id: 35 },
        { id: 36 },
        { id: 37 },
        { id: 38 },
        { id: 39 },
        { id: 40 },
        { id: 41 },
        { id: 42 },
        { id: 43 },
        { id: 44 },
        { id: 45 },
        { id: 46 },
        { id: 47 },
        { id: 48 },
        { id: 49 },
        { id: 50 },
        { id: 51 }
      ])
      .mockResolvedValueOnce([
        { id: 52 },
        { id: 53 },
        { id: 54 },
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
    expect(result.current.conversations).toHaveLength(50);
    expect(result.current.conversations[0]).toEqual({ id: 1 });
    expect(result.current.conversations[49]).toEqual({ id: 50 });

    await act(async () => {
      await result.current.loadMoreConversations();
    });

    expect(result.current.conversations).toHaveLength(53);
    expect(result.current.conversations.slice(-3)).toEqual([
      { id: 52 },
      { id: 53 },
      { id: 54 },
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

  it("ignores errors and loading cleanup from an obsolete refresh", async () => {
    let rejectFirst;
    let resolveLatest;
    listConversations
      .mockImplementationOnce(
        () =>
          new Promise((_resolve, reject) => {
            rejectFirst = reject;
          })
      )
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveLatest = resolve;
          })
      );

    const props = createProps();
    const { result } = renderHook(() => useConversationList(props));
    let firstRequest;
    let latestRequest;

    act(() => {
      firstRequest = result.current.refreshConversations();
      latestRequest = result.current.refreshConversations();
    });

    expect(result.current.conversationsLoading).toBe(true);

    await act(async () => {
      rejectFirst(new Error("obsolete refresh failed"));
      await firstRequest;
    });

    expect(result.current.conversationsLoading).toBe(true);
    expect(props.setToast).not.toHaveBeenCalled();

    await act(async () => {
      resolveLatest([{ id: 99 }]);
      await latestRequest;
    });

    expect(result.current.conversations).toEqual([{ id: 99 }]);
    expect(result.current.conversationsLoading).toBe(false);
    expect(props.setToast).not.toHaveBeenCalled();
  });

  it("keeps a reset refresh active when an obsolete load-more request fails", async () => {
    listConversations.mockResolvedValueOnce(
      Array.from({ length: 51 }, (_, index) => ({ id: index + 1 }))
    );

    const props = createProps();
    const { result } = renderHook(() => useConversationList(props));

    await act(async () => {
      await result.current.refreshConversations();
    });

    let rejectLoadMore;
    let resolveRefresh;
    listConversations
      .mockImplementationOnce(
        () =>
          new Promise((_resolve, reject) => {
            rejectLoadMore = reject;
          })
      )
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveRefresh = resolve;
          })
      );

    let loadMoreRequest;
    let refreshRequest;
    act(() => {
      loadMoreRequest = result.current.loadMoreConversations();
    });

    expect(result.current.conversationsLoadingMore).toBe(true);

    act(() => {
      refreshRequest = result.current.refreshConversations();
    });

    expect(result.current.conversationsLoading).toBe(true);
    expect(result.current.conversationsLoadingMore).toBe(false);

    await act(async () => {
      rejectLoadMore(new Error("obsolete page load failed"));
      await loadMoreRequest;
    });

    expect(result.current.conversationsLoading).toBe(true);
    expect(result.current.conversationsLoadingMore).toBe(false);
    expect(props.setToast).not.toHaveBeenCalled();

    await act(async () => {
      resolveRefresh([{ id: 200 }]);
      await refreshRequest;
    });

    expect(result.current.conversations).toEqual([{ id: 200 }]);
    expect(result.current.conversationsLoading).toBe(false);
    expect(result.current.conversationsLoadingMore).toBe(false);
    expect(props.setToast).not.toHaveBeenCalled();
  });

  it("uses the latest selected project when refreshing with default filters", async () => {
    const props = createProps();
    const { result, rerender } = renderHook(
      ({ selectedProjectId }) =>
        useConversationList({
          ...props,
          filters: { ...props.filters, selectedProjectId },
        }),
      { initialProps: { selectedProjectId: 3 } }
    );
    listConversations.mockResolvedValueOnce([]);

    rerender({ selectedProjectId: 99 });

    await act(async () => {
      await result.current.refreshConversations();
    });

    expect(listConversations).toHaveBeenCalledWith(
      false,
      null,
      2,
      99,
      "",
      false,
      null,
      0,
      51
    );
  });

});
