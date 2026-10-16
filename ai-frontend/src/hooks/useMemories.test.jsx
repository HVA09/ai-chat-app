import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useMemories from "./useMemories";

const { listMemories, createMemory, deleteMemory } = vi.hoisted(() => ({
  listMemories: vi.fn(),
  createMemory: vi.fn(),
  deleteMemory: vi.fn(),
}));

vi.mock("../lib/memoriesApi", () => ({
  listMemories,
  createMemory,
  deleteMemory,
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
  messages = [{ role: "user", text: "Remember this" }],
} = {}) {
  const setToast = vi.fn();
  const hook = renderHook(() =>
    useMemories({
      authed,
      messages,
      loading: false,
      readOnlyConversation: false,
      editingMessageIndex: null,
      setToast,
    })
  );
  return { ...hook, setToast };
}

describe("useMemories", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listMemories.mockResolvedValue([]);
    createMemory.mockResolvedValue({ id: 1, content: "Remember this" });
    deleteMemory.mockResolvedValue({});
  });

  it("loads memories successfully", async () => {
    const memories = [{ id: 3, content: "Existing memory" }];
    listMemories.mockResolvedValueOnce(memories);
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.refreshMemories();
    });

    expect(result.current.memories).toEqual(memories);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("does not restore memories when a pending refresh resolves after reset", async () => {
    const stale = [{ id: 8, content: "Previous account memory" }];
    let resolvePending;
    listMemories.mockImplementationOnce(
      () => new Promise((resolve) => {
        resolvePending = resolve;
      })
    );
    const { result, setToast } = setupHook();

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.refreshMemories();
    });
    act(() => {
      result.current.resetMemories();
    });

    await act(async () => {
      resolvePending(stale);
      await pendingRequest;
    });

    expect(result.current.memories).toEqual([]);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("keeps the newest result when overlapping refreshes resolve out of order", async () => {
    const stale = [{ id: 8, content: "Older response" }];
    const current = [{ id: 9, content: "Newest response" }];
    let resolveOlder;
    let resolveCurrent;
    listMemories
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
      olderRequest = result.current.refreshMemories();
      currentRequest = result.current.refreshMemories();
    });

    await act(async () => {
      resolveCurrent(current);
      await currentRequest;
    });
    await act(async () => {
      resolveOlder(stale);
      await olderRequest;
    });

    expect(result.current.memories).toEqual(current);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("ignores a stale load failure after reset instead of showing an error toast", async () => {
    let rejectPending;
    listMemories.mockImplementationOnce(
      () => new Promise((_resolve, reject) => {
        rejectPending = reject;
      })
    );
    const { result, setToast } = setupHook();

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.refreshMemories();
    });
    act(() => {
      result.current.resetMemories();
    });

    await act(async () => {
      rejectPending(new Error("previous session failed"));
      await pendingRequest;
    });

    expect(result.current.memories).toEqual([]);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("does not restore a memory after a create request completes following reset", async () => {
    let resolveCreate;
    createMemory.mockImplementationOnce(
      () => new Promise((resolve) => {
        resolveCreate = resolve;
      })
    );
    const { result, setToast } = setupHook();

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.handleToggleMessageMemory(0);
    });
    act(() => {
      result.current.resetMemories();
    });

    await act(async () => {
      resolveCreate({ id: 10, content: "Remember this" });
      await pendingRequest;
    });

    expect(result.current.memories).toEqual([]);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("preserves the current account state when a memory deletion finishes after reset", async () => {
    const existing = [{ id: 11, content: "Remember this" }];
    listMemories.mockResolvedValueOnce(existing);
    let resolveDelete;
    deleteMemory.mockImplementationOnce(
      () => new Promise((resolve) => {
        resolveDelete = resolve;
      })
    );
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.refreshMemories();
    });
    expect(result.current.memories).toEqual(existing);

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.handleToggleMessageMemory(0);
    });
    act(() => {
      result.current.resetMemories();
    });

    await act(async () => {
      resolveDelete({});
      await pendingRequest;
    });

    expect(result.current.memories).toEqual([]);
    expect(setToast).not.toHaveBeenCalled();
  });
});
