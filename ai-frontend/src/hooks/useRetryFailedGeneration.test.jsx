import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { streamRegenerateMessage } from "../lib/chatApi";
import useRetryFailedGeneration from "./useRetryFailedGeneration";

vi.mock("../lib/chatApi", () => ({
  streamRegenerateMessage: vi.fn(),
}));

function makeProps(overrides = {}) {
  let messages = [{ role: "user", text: "Question" }];
  const messageCountRef = { current: 1 };
  const streamAbortRef = { current: null };
  const setMessages = vi.fn((next) => {
    messages = typeof next === "function" ? next(messages) : next;
  });

  const props = {
    readOnlyConversation: false,
    loading: false,
    retryableUserMessage: {
      conversationId: "conversation-1",
      text: "Question",
    },
    conversationId: "conversation-1",
    setError: vi.fn(),
    setLoading: vi.fn(),
    setRetryableUserMessage: vi.fn(),
    messageCountRef,
    setMessages,
    streamAbortRef,
    setConversationId: vi.fn(),
    appendToLastMessage: (chunk) => {
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        next[next.length - 1] = { ...last, text: last.text + chunk };
        return next;
      });
    },
    refreshConversations: vi.fn(),
    showArchivedConversations: false,
    selectedFolderId: null,
    selectedWorkspaceId: "workspace-1",
    selectedProjectId: "project-1",
    conversationSearch: "report",
    showTrashConversations: false,
    selectedTagId: "tag-1",
    maybeAutoSummarizeConversation: vi.fn(),
    ...overrides,
  };

  return { props, getMessages: () => messages };
}

describe("useRetryFailedGeneration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("retries the failed response and refreshes the active conversation list", async () => {
    const { props, getMessages } = makeProps();
    streamRegenerateMessage.mockImplementationOnce(async (_id, options) => {
      options.onConversationId("conversation-1");
      options.onSources([{ title: "Source" }]);
      options.onChunk("Re");
      options.onChunk("tried answer");
      options.onDone();
    });

    const { result } = renderHook(() => useRetryFailedGeneration(props));
    await act(async () => {
      await result.current.retryFailedGeneration();
    });

    expect(streamRegenerateMessage).toHaveBeenCalledWith(
      "conversation-1",
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(props.setLoading).toHaveBeenNthCalledWith(1, true);
    expect(props.setLoading).toHaveBeenLastCalledWith(false);
    expect(props.setRetryableUserMessage).toHaveBeenCalledWith(null);
    expect(props.setConversationId).toHaveBeenCalledWith("conversation-1");
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false,
      null,
      "workspace-1",
      "project-1",
      "report",
      false,
      "tag-1"
    );
    expect(props.maybeAutoSummarizeConversation).toHaveBeenCalledWith(
      "conversation-1",
      2
    );
    expect(props.streamAbortRef.current).toBe(null);
    expect(getMessages()).toEqual([
      { role: "user", text: "Question" },
      {
        role: "assistant",
        text: "Retried answer",
        time: expect.any(String),
        feedback: null,
        sources: [{ title: "Source" }],
      },
    ]);
  });

  it("removes the empty assistant placeholder and restores retry state after an error", async () => {
    const { props, getMessages } = makeProps();
    streamRegenerateMessage.mockImplementationOnce(async (_id, options) => {
      options.onError("temporary failure");
    });

    const { result } = renderHook(() => useRetryFailedGeneration(props));
    await act(async () => {
      await result.current.retryFailedGeneration();
    });

    expect(props.setError).toHaveBeenCalledWith("temporary failure");
    expect(props.setLoading).toHaveBeenLastCalledWith(false);
    expect(props.streamAbortRef.current).toBe(null);
    expect(props.messageCountRef.current).toBe(1);
    expect(getMessages()).toEqual([{ role: "user", text: "Question" }]);
    expect(props.setRetryableUserMessage).toHaveBeenLastCalledWith({
      conversationId: "conversation-1",
      text: "Question",
    });
  });

  it.each([
    ["read-only conversation", { readOnlyConversation: true }],
    ["already loading", { loading: true }],
    ["no active conversation", { conversationId: null }],
    ["no retry payload", { retryableUserMessage: null }],
    [
      "retry belongs to another conversation",
      { retryableUserMessage: { conversationId: "conversation-2", text: "Question" } },
    ],
  ])("does not start a retry when %s", async (_name, overrides) => {
    const { props } = makeProps(overrides);
    const { result } = renderHook(() => useRetryFailedGeneration(props));

    await act(async () => {
      await result.current.retryFailedGeneration();
    });

    expect(streamRegenerateMessage).not.toHaveBeenCalled();
    expect(props.setMessages).not.toHaveBeenCalled();
    expect(props.setLoading).not.toHaveBeenCalled();
  });
});
