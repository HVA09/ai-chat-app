import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useBookmarks from "./useBookmarks";

const { listBookmarkedMessages, toggleMessageBookmark } = vi.hoisted(() => ({
  listBookmarkedMessages: vi.fn(),
  toggleMessageBookmark: vi.fn(),
}));

vi.mock("../lib/bookmarksApi", () => ({
  listBookmarkedMessages,
  toggleMessageBookmark,
}));

vi.mock("react-i18next", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useTranslation: () => ({ t: (key) => key }),
  };
});

function setupHook({
  authed = false,
  conversationId = 1,
  setMessages = vi.fn(),
} = {}) {
  const setToast = vi.fn();
  const openConversation = vi.fn();
  const hook = renderHook(() =>
    useBookmarks({
      authed,
      conversationId,
      loading: false,
      readOnlyConversation: false,
      setMessages,
      setToast,
      openConversation,
    })
  );
  return { ...hook, setToast, setMessages, openConversation };
}

describe("useBookmarks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listBookmarkedMessages.mockResolvedValue([]);
    toggleMessageBookmark.mockResolvedValue({ bookmarked: true });
  });

  it("loads bookmarks successfully", async () => {
    const bookmarks = [{ id: 3, conversation_id: 1, message_index: 2 }];
    listBookmarkedMessages.mockResolvedValueOnce(bookmarks);
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.refreshBookmarkedMessages();
    });

    expect(result.current.bookmarkedMessages).toEqual(bookmarks);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("does not restore bookmarks when a pending refresh resolves after reset", async () => {
    const stale = [{ id: 8, conversation_id: 1, message_index: 1 }];
    let resolvePending;
    listBookmarkedMessages.mockImplementationOnce(
      () => new Promise((resolve) => {
        resolvePending = resolve;
      })
    );
    const { result, setToast } = setupHook();

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.refreshBookmarkedMessages();
    });
    act(() => {
      result.current.resetBookmarks();
    });

    await act(async () => {
      resolvePending(stale);
      await pendingRequest;
    });

    expect(result.current.bookmarkedMessages).toEqual([]);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("keeps the newest result when overlapping refreshes resolve out of order", async () => {
    const stale = [{ id: 8, conversation_id: 1, message_index: 1 }];
    const current = [{ id: 9, conversation_id: 2, message_index: 3 }];
    let resolveOlder;
    let resolveCurrent;
    listBookmarkedMessages
      .mockImplementationOnce(
        () => new Promise((resolve) => {
          resolveOlder = resolve;
        })
      )
      .mockImplementationOnce(
        () => new Promise((resolve) => {
          resolveCurrent = resolve;
        })
      );
    const { result, setToast } = setupHook();

    let olderRequest;
    let currentRequest;
    act(() => {
      olderRequest = result.current.refreshBookmarkedMessages();
      currentRequest = result.current.refreshBookmarkedMessages();
    });

    await act(async () => {
      resolveCurrent(current);
      await currentRequest;
    });
    await act(async () => {
      resolveOlder(stale);
      await olderRequest;
    });

    expect(result.current.bookmarkedMessages).toEqual(current);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("ignores a stale load failure after reset instead of showing an error toast", async () => {
    let rejectPending;
    listBookmarkedMessages.mockImplementationOnce(
      () => new Promise((_resolve, reject) => {
        rejectPending = reject;
      })
    );
    const { result, setToast } = setupHook();

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.refreshBookmarkedMessages();
    });
    act(() => {
      result.current.resetBookmarks();
    });

    await act(async () => {
      rejectPending(new Error("previous session failed"));
      await pendingRequest;
    });

    expect(result.current.bookmarkedMessages).toEqual([]);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("does not apply an old bookmark toggle to a newly selected conversation", async () => {
    let resolveToggle;
    toggleMessageBookmark.mockImplementationOnce(
      () => new Promise((resolve) => {
        resolveToggle = resolve;
      })
    );
    const setMessages = vi.fn();
    const setToast = vi.fn();
    const openConversation = vi.fn();
    const { result, rerender } = renderHook(
      ({ conversationId }) =>
        useBookmarks({
          authed: false,
          conversationId,
          loading: false,
          readOnlyConversation: false,
          setMessages,
          setToast,
          openConversation,
        }),
      { initialProps: { conversationId: 1 } }
    );

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.handleToggleMessageBookmark(0);
    });
    rerender({ conversationId: 2 });

    await act(async () => {
      resolveToggle({ bookmarked: true });
      await pendingRequest;
    });

    expect(toggleMessageBookmark).toHaveBeenCalledWith(1, 1);
    expect(setMessages).not.toHaveBeenCalled();
    expect(result.current.bookmarkedMessages).toEqual([]);
    expect(setToast).not.toHaveBeenCalled();
    expect(listBookmarkedMessages).toHaveBeenCalledTimes(1);
  });

  it("does not restore bookmark state after a pending toggle finishes following reset", async () => {
    let resolveToggle;
    toggleMessageBookmark.mockImplementationOnce(
      () => new Promise((resolve) => {
        resolveToggle = resolve;
      })
    );
    const { result, setToast, setMessages } = setupHook();

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.handleToggleMessageBookmark(0);
    });
    act(() => {
      result.current.resetBookmarks();
    });

    await act(async () => {
      resolveToggle({ bookmarked: true });
      await pendingRequest;
    });

    expect(result.current.bookmarkedMessages).toEqual([]);
    expect(setMessages).not.toHaveBeenCalled();
    expect(setToast).not.toHaveBeenCalled();
    expect(listBookmarkedMessages).not.toHaveBeenCalled();
  });
});
