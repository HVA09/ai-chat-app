import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useAiModels from "./useAiModels";

const { listAiModels } = vi.hoisted(() => ({
  listAiModels: vi.fn(),
}));

vi.mock("../lib/chatApi", () => ({ listAiModels }));

vi.mock("react-i18next", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useTranslation: () => ({ t: (key) => key }),
  };
});

function setupHook() {
  const setToast = vi.fn();
  const hook = renderHook(() => useAiModels({ setToast }));
  return { ...hook, setToast };
}

describe("useAiModels", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAiModels.mockResolvedValue([]);
  });

  it("loads an array of models and selects the configured default", async () => {
    const models = [
      { id: "model-a", is_default: false },
      { id: "model-b", is_default: true },
    ];
    listAiModels.mockResolvedValueOnce(models);
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.refreshAiModels();
    });

    expect(result.current.aiModels).toEqual(models);
    expect(result.current.selectedModel).toBe("model-b");
    expect(setToast).not.toHaveBeenCalled();
  });

  it("accepts the wrapped API response and preserves an available user selection", async () => {
    listAiModels.mockResolvedValueOnce({
      models: [
        { id: "model-a", is_default: true },
        { id: "model-b", is_default: false },
      ],
    });
    const { result } = setupHook();

    await act(async () => {
      await result.current.refreshAiModels();
    });
    act(() => {
      result.current.setSelectedModel("model-b");
    });
    listAiModels.mockResolvedValueOnce({
      models: [
        { id: "model-a", is_default: true },
        { id: "model-b", is_default: false },
      ],
    });

    await act(async () => {
      await result.current.refreshAiModels();
    });

    expect(result.current.selectedModel).toBe("model-b");
  });

  it("does not restore models when a pending refresh resolves after reset", async () => {
    const staleModels = [{ id: "previous-session-model", is_default: true }];
    let resolvePending;
    listAiModels.mockImplementationOnce(
      () => new Promise((resolve) => {
        resolvePending = resolve;
      })
    );
    const { result, setToast } = setupHook();

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.refreshAiModels();
    });
    act(() => {
      result.current.resetAiModels();
    });

    await act(async () => {
      resolvePending(staleModels);
      await pendingRequest;
    });

    expect(result.current.aiModels).toEqual([]);
    expect(result.current.selectedModel).toBe("");
    expect(setToast).not.toHaveBeenCalled();
  });

  it("keeps the newest result when overlapping refreshes resolve out of order", async () => {
    const olderModels = [{ id: "older", is_default: true }];
    const newestModels = [{ id: "newest", is_default: true }];
    let resolveOlder;
    let resolveNewest;
    listAiModels
      .mockImplementationOnce(
        () => new Promise((resolve) => {
          resolveOlder = resolve;
        })
      )
      .mockImplementationOnce(
        () => new Promise((resolve) => {
          resolveNewest = resolve;
        })
      );
    const { result, setToast } = setupHook();

    let olderRequest;
    let newestRequest;
    act(() => {
      olderRequest = result.current.refreshAiModels();
      newestRequest = result.current.refreshAiModels();
    });

    await act(async () => {
      resolveNewest(newestModels);
      await newestRequest;
    });
    await act(async () => {
      resolveOlder(olderModels);
      await olderRequest;
    });

    expect(result.current.aiModels).toEqual(newestModels);
    expect(result.current.selectedModel).toBe("newest");
    expect(setToast).not.toHaveBeenCalled();
  });

  it("ignores a stale refresh failure after reset instead of showing an error toast", async () => {
    let rejectPending;
    listAiModels.mockImplementationOnce(
      () => new Promise((_resolve, reject) => {
        rejectPending = reject;
      })
    );
    const { result, setToast } = setupHook();

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.refreshAiModels();
    });
    act(() => {
      result.current.resetAiModels();
    });

    await act(async () => {
      rejectPending(new Error("previous session failed"));
      await pendingRequest;
    });

    expect(result.current.aiModels).toEqual([]);
    expect(result.current.selectedModel).toBe("");
    expect(setToast).not.toHaveBeenCalled();
  });

  it("shows a translated fallback when the active model refresh fails", async () => {
    listAiModels.mockRejectedValueOnce(new Error("offline"));
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.refreshAiModels();
    });

    expect(setToast).toHaveBeenCalledWith({
      message: "app.aiModelsLoadError",
      type: "error",
    });
    expect(result.current.aiModels).toEqual([]);
  });
});
