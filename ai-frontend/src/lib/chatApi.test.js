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

    expect(onError).toHaveBeenCalledWith("تعذر الاتصال بالخادم", {
      kind: "transport",
      messagePersisted: true,
    });
  });
});


describe("chatApi agent tool activity", () => {
  it("parses agent tool activity SSE events", async () => {
    const onToolEvent = vi.fn();
    const onDone = vi.fn();
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

    await streamChatMessage("hello", null, null, {
      onToolEvent,
      onDone,
    });

    expect(onToolEvent).toHaveBeenNthCalledWith(1, { type: "start", name: "calculator" });
    expect(onToolEvent).toHaveBeenNthCalledWith(2, {
      type: "result",
      name: "calculator",
      ok: true,
      duration_ms: 18,
    });
    expect(onDone).toHaveBeenCalledTimes(1);
  });
});


describe("chatApi file attachments", () => {
  it("sends uploaded file IDs in the streaming request body", async () => {
    const encoder = new TextEncoder();
    let index = 0;
    const chunks = ['event: done\ndata: {}\n\n'];
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
    const onDone = vi.fn();

    await streamChatMessage("Summarize this upload", null, null, {
      fileIds: [41, 42],
      onDone,
    });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/chat/stream"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          message: "Summarize this upload",
          conversation_id: null,
          assistant_id: null,
          workspace_id: null,
          project_id: null,
          model: null,
          file_ids: [41, 42],
        }),
      })
    );
    expect(onDone).toHaveBeenCalledTimes(1);
  });
});
