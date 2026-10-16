import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useTagManagement from "./useTagManagement";

const { createTag, deleteTag, listTags, setConversationTags, updateTag } = vi.hoisted(() => ({
  createTag: vi.fn(),
  deleteTag: vi.fn(),
  listTags: vi.fn(),
  setConversationTags: vi.fn(),
  updateTag: vi.fn(),
}));

vi.mock("../lib/tagsApi", () => ({
  createTag,
  deleteTag,
  listTags,
  setConversationTags,
  updateTag,
}));

function createProps(overrides = {}) {
  return {
    t: (key) => key,
    selectedTagId: null,
    setSelectedTagId: vi.fn(),
    setTags: vi.fn(),
    setSelectedConversationIds: vi.fn(),
    startNewChat: vi.fn(),
    refreshConversations: vi.fn().mockResolvedValue([]),
    showArchivedConversations: false,
    selectedFolderId: null,
    selectedWorkspaceId: 2,
    selectedProjectId: null,
    conversationSearch: "",
    showTrashConversations: false,
    setToast: vi.fn(),
    tagRequestGenerationRef: { current: 0 },
    ...overrides,
  };
}

describe("useTagManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listTags.mockResolvedValue([]);
    createTag.mockResolvedValue({ id: 7, name: "Tag" });
    updateTag.mockResolvedValue({});
    deleteTag.mockResolvedValue({});
    setConversationTags.mockResolvedValue({});
  });

  it("selects a tag, clears selections, starts a fresh chat, and refreshes", async () => {
    const props = createProps();
    const { result } = renderHook(() => useTagManagement(props));

    await act(async () => {
      await result.current.handleSelectTag("7");
    });

    expect(props.setSelectedTagId).toHaveBeenCalledWith(7);
    expect(props.setSelectedConversationIds).toHaveBeenCalledWith([]);
    expect(props.startNewChat).toHaveBeenCalled();
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, 2, null, "", false, 7);
  });

  it("only applies the newest tag refresh when requests resolve out of order", async () => {
    const olderTags = [{ id: 1, name: "Older workspace tag" }];
    const newerTags = [{ id: 2, name: "Current workspace tag" }];
    let resolveOlder;
    let resolveNewer;
    listTags
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOlder = resolve; }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveNewer = resolve; }));
    const props = createProps();
    const { result } = renderHook(() => useTagManagement(props));

    let olderRequest;
    let newerRequest;
    act(() => {
      olderRequest = result.current.refreshTags();
      newerRequest = result.current.refreshTags();
    });

    await act(async () => {
      resolveNewer(newerTags);
      await newerRequest;
    });
    await act(async () => {
      resolveOlder(olderTags);
      await olderRequest;
    });

    expect(props.setTags).toHaveBeenCalledTimes(1);
    expect(props.setTags).toHaveBeenCalledWith(newerTags);
    expect(props.setToast).not.toHaveBeenCalled();
  });

  it("does not restore tags when a pending refresh resolves after logout invalidation", async () => {
    const previousSessionTags = [{ id: 8, name: "Previous session tag" }];
    const tagRequestGenerationRef = { current: 0 };
    let resolvePending;
    listTags.mockImplementationOnce(() => new Promise((resolve) => { resolvePending = resolve; }));
    const props = createProps({ tagRequestGenerationRef });
    const { result } = renderHook(() => useTagManagement(props));

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.refreshTags();
    });
    tagRequestGenerationRef.current += 1;
    props.setTags([]);

    await act(async () => {
      resolvePending(previousSessionTags);
      await pendingRequest;
    });

    expect(props.setTags).toHaveBeenCalledTimes(1);
    expect(props.setTags).toHaveBeenCalledWith([]);
    expect(props.setToast).not.toHaveBeenCalled();
  });

  it("does not show a stale tag load failure after logout invalidates the request", async () => {
    const tagRequestGenerationRef = { current: 0 };
    let rejectPending;
    listTags.mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectPending = reject; }));
    const props = createProps({ tagRequestGenerationRef });
    const { result } = renderHook(() => useTagManagement(props));

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.refreshTags();
    });
    tagRequestGenerationRef.current += 1;

    await act(async () => {
      rejectPending(new Error("previous session request failed"));
      await pendingRequest;
    });

    expect(props.setToast).not.toHaveBeenCalled();
  });

  it("shows the translated fallback when the current tag refresh fails", async () => {
    listTags.mockRejectedValueOnce(new Error("offline"));
    const props = createProps();
    const { result } = renderHook(() => useTagManagement(props));

    await act(async () => {
      await result.current.refreshTags();
    });

    expect(props.setToast).toHaveBeenCalledWith({
      message: "app.tagsLoadError",
      type: "error",
    });
    expect(props.setTags).not.toHaveBeenCalled();
  });
});
