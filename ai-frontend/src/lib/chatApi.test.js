import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { streamChatMessage } from "./chatApi";

describe("chatApi streaming error handling", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("calls onDone when the request is aborted", async () => {
    const onDone = vi.fn();
    const controller = new AbortController();

    globalThis.fetch = vi.fn().mockRejectedValue(
      Object.assign(new Error("aborted"), { name: "AbortError" })
    );

    await streamChatMessage("hello", null, null, {
      signal: controller.signal,
      onDone,
    });

    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it("reports a reader transport error instead of rejecting", async () => {
    const onError = vi.fn();
    const reader = {
      read: vi.fn().mockRejectedValue(new Error("network dropped")),
      cancel: vi.fn().mockResolvedValue(undefined),
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: { getReader: () => reader },
    });

    await expect(
      streamChatMessage("hello", null, null, { onError })
    ).resolves.toBeUndefined();

    expect(onError).toHaveBeenCalledWith("تعذر الاتصال بالخادم");
  });
});
