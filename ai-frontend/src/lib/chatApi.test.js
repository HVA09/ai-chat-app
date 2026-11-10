import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { streamChatMessage, streamRegenerateMessage, streamEditMessage } from "./chatApi";
import i18n from "../i18n";

describe("chatApi streaming error handling", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(async () => {
    globalThis.fetch = originalFetch;
    await i18n.changeLanguage("ar");
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

  it("sends the active UI language with all streaming requests", async () => {
    await i18n.changeLanguage("en");

    const requestFunctions = [
      () => streamChatMessage("hello", null, null, { onError: vi.fn() }),
      () => streamRegenerateMessage(7, { onError: vi.fn() }),
      () => streamEditMessage(7, 1, "updated", { onError: vi.fn() }),
    ];

    for (const invoke of requestFunctions) {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: vi.fn().mockResolvedValue({ detail: "provider error" }),
      });

      await invoke();

      expect(globalThis.fetch).toHaveBeenCalledTimes(1);
      expect(globalThis.fetch.mock.calls[0][1].headers).toMatchObject({
        "Accept-Language": "en",
      });
    }
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


describe("chatApi Agent retry safety", () => {
  it("preserves a blocked retry mode when a tool started before the Agent failure", async () => {
    const onError = vi.fn();
    const encoder = new TextEncoder();
    const chunks = [
      "event: retry_mode\ndata: blocked\n\n",
      "event: error\ndata: The Agent task failed after a tool started.\n\n",
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

    await streamChatMessage("update a project file", 7, null, { onError });

    expect(onError).toHaveBeenCalledWith(
      "The Agent task failed after a tool started.",
      {
        kind: "stream",
        messagePersisted: false,
        retryMode: "blocked",
      }
    );
  });

  it("blocks an Agent retry when request transport fails before a response arrives", async () => {
    const onError = vi.fn();
    const onDone = vi.fn();
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("network dropped"));

    await streamChatMessage("/agent update the project file", 7, null, {
      onError,
      onDone,
    });

    expect(onError).toHaveBeenCalledWith(
      expect.stringContaining("انقطع الاتصال"),
      expect.objectContaining({
        kind: "transport",
        messagePersisted: false,
        retryMode: "blocked",
      })
    );
    expect(onDone).not.toHaveBeenCalled();
  });

  it("blocks an Agent retry when the stream drops after a tool-start event", async () => {
    const onError = vi.fn();
    const onToolEvent = vi.fn();
    const encoder = new TextEncoder();
    const reader = {
      read: vi.fn()
        .mockResolvedValueOnce({
          done: false,
          value: encoder.encode('event: tool\ndata: {"type":"start","name":"edit_project_file"}\n\n'),
        })
        .mockRejectedValueOnce(new Error("network dropped")),
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: { getReader: () => reader },
    });

    await streamChatMessage("/agent update the project file", 7, null, {
      onError,
      onToolEvent,
    });

    expect(onToolEvent).toHaveBeenCalledWith({
      type: "start",
      name: "edit_project_file",
    });
    expect(onError).toHaveBeenCalledWith(
      expect.stringContaining("انقطع الاتصال"),
      expect.objectContaining({
        kind: "transport",
        messagePersisted: false,
        retryMode: "blocked",
      })
    );
  });

  it("blocks an Agent retry when the stream ends without a terminal event", async () => {
    const onError = vi.fn();
    const encoder = new TextEncoder();
    let index = 0;
    const chunks = ["event: conversation\ndata: 7\n\n"];
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

    await streamChatMessage("/agent update the project file", 7, null, { onError });

    expect(onError).toHaveBeenCalledWith(
      expect.stringContaining("انقطع الاتصال"),
      expect.objectContaining({
        kind: "transport",
        messagePersisted: false,
        retryMode: "blocked",
      })
    );
  });

  it("does not trust a safe-send marker after a tool-start event", async () => {
    const onError = vi.fn();
    const encoder = new TextEncoder();
    const chunks = [
      'event: tool\ndata: {"type":"start","name":"edit_project_file"}\n\n',
      "event: retry_mode\ndata: send\n\n",
      "event: error\ndata: retry marker mismatch\n\n",
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

    await streamChatMessage("/agent update the project file", 7, null, { onError });

    expect(onError).toHaveBeenCalledWith(
      "retry marker mismatch",
      expect.objectContaining({
        kind: "stream",
        messagePersisted: false,
        retryMode: "blocked",
      })
    );
  });

  it("keeps explicit safe-send mode for an Agent failure before any tool starts", async () => {
    const onError = vi.fn();
    const encoder = new TextEncoder();
    const chunks = [
      "event: retry_mode\ndata: send\n\n",
      "event: error\ndata: provider failed before tool execution\n\n",
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

    await streamChatMessage("/agent update the project file", 7, null, { onError });

    expect(onError).toHaveBeenCalledWith(
      "provider failed before tool execution",
      {
        kind: "stream",
        messagePersisted: false,
        retryMode: "send",
      }
    );
  });
});

