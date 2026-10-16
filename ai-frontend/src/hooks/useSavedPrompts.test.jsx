import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useSavedPrompts from "./useSavedPrompts";

const {
  createSavedPrompt,
  deleteSavedPrompt,
  listSavedPrompts,
  updateSavedPrompt,
} = vi.hoisted(() => ({
  createSavedPrompt: vi.fn(),
  deleteSavedPrompt: vi.fn(),
  listSavedPrompts: vi.fn(),
  updateSavedPrompt: vi.fn(),
}));

vi.mock("../lib/savedPromptsApi", () => ({
  createSavedPrompt,
  deleteSavedPrompt,
  listSavedPrompts,
  updateSavedPrompt,
}));

vi.mock("react-i18next", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useTranslation: () => ({ t: (key) => key }),
  };
});

describe("useSavedPrompts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listSavedPrompts.mockResolvedValue([]);
    createSavedPrompt.mockResolvedValue({});
    deleteSavedPrompt.mockResolvedValue({});
    updateSavedPrompt.mockResolvedValue({});
  });

  it("loads saved prompts successfully", async () => {
    const prompts = [{ id: 1, name: "Useful prompt", content: "Summarize this" }];
    const setToast = vi.fn();
    listSavedPrompts.mockResolvedValueOnce(prompts);

    const { result } = renderHook(() => useSavedPrompts({ setToast }));

    await act(async () => {
      await result.current.refreshSavedPrompts();
    });

    expect(result.current.savedPrompts).toEqual(prompts);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("does not restore saved prompts when a pending refresh resolves after reset", async () => {
    const existing = [{ id: 1, name: "Previous", content: "Old account data" }];
    const stale = [{ id: 2, name: "Stale", content: "Must not return" }];
    let resolvePending;
    listSavedPrompts.mockResolvedValueOnce(existing).mockImplementationOnce(
      () => new Promise((resolve) => {
        resolvePending = resolve;
      })
    );
    const setToast = vi.fn();
    const { result } = renderHook(() => useSavedPrompts({ setToast }));

    await act(async () => {
      await result.current.refreshSavedPrompts();
    });
    expect(result.current.savedPrompts).toEqual(existing);

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.refreshSavedPrompts();
    });
    act(() => {
      result.current.resetSavedPrompts();
    });
    expect(result.current.savedPrompts).toEqual([]);

    await act(async () => {
      resolvePending(stale);
      await pendingRequest;
    });

    expect(result.current.savedPrompts).toEqual([]);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("keeps the newest result when overlapping refreshes resolve out of order", async () => {
    const stale = [{ id: 1, name: "Stale", content: "Older response" }];
    const current = [{ id: 2, name: "Current", content: "Latest response" }];
    let resolveOlder;
    let resolveCurrent;
    listSavedPrompts
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
    const setToast = vi.fn();
    const { result } = renderHook(() => useSavedPrompts({ setToast }));

    let olderRequest;
    let currentRequest;
    act(() => {
      olderRequest = result.current.refreshSavedPrompts();
      currentRequest = result.current.refreshSavedPrompts();
    });

    await act(async () => {
      resolveCurrent(current);
      await currentRequest;
    });
    await act(async () => {
      resolveOlder(stale);
      await olderRequest;
    });

    expect(result.current.savedPrompts).toEqual(current);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("ignores a stale load failure after reset instead of showing a toast", async () => {
    let rejectPending;
    listSavedPrompts.mockImplementationOnce(
      () => new Promise((_resolve, reject) => {
        rejectPending = reject;
      })
    );
    const setToast = vi.fn();
    const { result } = renderHook(() => useSavedPrompts({ setToast }));

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.refreshSavedPrompts();
    });
    act(() => {
      result.current.resetSavedPrompts();
    });

    await act(async () => {
      rejectPending(new Error("previous session failed"));
      await pendingRequest;
    });

    expect(result.current.savedPrompts).toEqual([]);
    expect(setToast).not.toHaveBeenCalled();
  });
});
