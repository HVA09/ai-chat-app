import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useStopGeneration from "./useStopGeneration";

describe("useStopGeneration", () => {
  it("aborts the active stream and clears the active UI state", () => {
    const controller = { abort: vi.fn() };
    const streamAbortRef = { current: controller };
    const setLoading = vi.fn();
    const setToolActivity = vi.fn();
    const { result } = renderHook(() =>
      useStopGeneration({ streamAbortRef, setLoading, setToolActivity })
    );

    act(() => result.current.stopGeneration());

    expect(controller.abort).toHaveBeenCalledOnce();
    expect(streamAbortRef.current).toBeNull();
    expect(setLoading).toHaveBeenCalledWith(false);
    expect(setToolActivity).toHaveBeenCalledWith(null);
  });

  it("clears UI state safely when there is no active stream controller", () => {
    const streamAbortRef = { current: null };
    const setLoading = vi.fn();
    const setToolActivity = vi.fn();
    const { result } = renderHook(() =>
      useStopGeneration({ streamAbortRef, setLoading, setToolActivity })
    );

    act(() => result.current.stopGeneration());

    expect(streamAbortRef.current).toBeNull();
    expect(setLoading).toHaveBeenCalledWith(false);
    expect(setToolActivity).toHaveBeenCalledWith(null);
  });
});
