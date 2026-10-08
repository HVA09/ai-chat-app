import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { streamRegenerateMessage } from "../lib/chatApi";
import useRegenerateLastResponse from "./useRegenerateLastResponse";

vi.mock("../lib/chatApi", () => ({
  streamRegenerateMessage: vi.fn(),
}));

describe("useRegenerateLastResponse", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("regenerates the last assistant response and restores it on stream error", async () => {
    const stream = vi.fn(async (_id, options) => {
      options.onConversationId("conversation-2");
      options.onChunk("new ");
      options.onChunk("answer");
      options.onSources([{ title: "source" }]);
      options.onError("failed");
    });
    streamRegenerateMessage.mockImplementation(stream);

    let state = [
      { role: "user", text: "Question" },
      { role: "assistant", text: "Previous", feedback: "up" },
    ];
    const setMessages = vi.fn((next) => {
      state = typeof next === "function" ? next(state) : next;
    });
    const props = {
      readOnlyConversation: false,
      conversationId: "conversation-1",
      loading: false,
      lastAssistantIndex: 1,
      messages: state,
      autoSummaryLastMessageCountRef: { current: {} },
      streamAbortRef: { current: null },
      messageCountRef: { current: 2 },
      setRetryableUserMessage: vi.fn(),
      setError: vi.fn(),
      setMessages,
      setLoading: vi.fn(),
      setConversationId: vi.fn(),
      refreshConversations: vi.fn(),
      showArchivedConversations: false,
      selectedFolderId: null,
      selectedWorkspaceId: null,
      selectedProjectId: null,
      maybeAutoSummarizeConversation: vi.fn(),
    };

    const { result } = renderHook(() => useRegenerateLastResponse(props));
    await result.current.regenerateLastResponse();

    expect(stream).toHaveBeenCalledWith(
      "conversation-1",
      expect.objectContaining({
        signal: expect.any(AbortSignal),
      })
    );
    expect(props.setLoading).toHaveBeenCalledWith(true);
    expect(props.setConversationId).toHaveBeenCalledWith("conversation-2");
    expect(props.setError).toHaveBeenCalledWith("failed");
    expect(state[1].text).toBe("Previous");
    expect(state[1].feedback).toBe(null);
    expect(props.streamAbortRef.current).toBe(null);
  });

  it("does nothing when regeneration is not allowed", async () => {
    const props = {
      readOnlyConversation: true,
      conversationId: "conversation-1",
      loading: false,
      lastAssistantIndex: 1,
      messages: [{ text: "answer" }],
      autoSummaryLastMessageCountRef: { current: {} },
      streamAbortRef: { current: null },
      messageCountRef: { current: 1 },
      setRetryableUserMessage: vi.fn(),
      setError: vi.fn(),
      setMessages: vi.fn(),
      setLoading: vi.fn(),
      setConversationId: vi.fn(),
      refreshConversations: vi.fn(),
      showArchivedConversations: false,
      selectedFolderId: null,
      selectedWorkspaceId: null,
      selectedProjectId: null,
      maybeAutoSummarizeConversation: vi.fn(),
    };

    const { result } = renderHook(() => useRegenerateLastResponse(props));
    await result.current.regenerateLastResponse();

    expect(streamRegenerateMessage).not.toHaveBeenCalled();
    expect(props.setMessages).not.toHaveBeenCalled();
  });
});
