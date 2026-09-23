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


  it("parses agent tool activity SSE events", async () => {
    const onToolEvent = vi.fn();
    const encoder = new TextEncoder();
    const chunks = [
      'event: conversation\ndata: 7\n\n',
      'event: tool\ndata: {"type":"start","name":"calculator"}\n\n',
      'event: tool\ndata: {"type":"result","name":"calculator","ok":true,"duration_ms":18}\n\n',
      'event: chunk\ndata: الناتج\n\n',
      'event: done\ndata: {}\n\n',
    ];
    let index = 0;

    const reader = {
      read: vi.fn(async () => {
        if (index >= chunks.length) return { done: true, value: undefined };
        return { done: false, value: encoder.encode(chunks[index++]) };
      }),
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: { getReader: () => reader },
    });

    await streamChatMessage("hello", null, null, { onToolEvent });

    expect(onToolEvent).toHaveBeenCalledTimes(2);
    expect(onToolEvent).toHaveBeenNthCalledWith(1, {
      type: "start",
      name: "calculator",
    });
    expect(onToolEvent).toHaveBeenNthCalledWith(2, {
      type: "result",
      name: "calculator",
      ok: true,
      duration_ms: 18,
    });
  });
