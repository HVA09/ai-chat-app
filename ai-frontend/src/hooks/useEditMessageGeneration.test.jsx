import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { streamEditMessage } from "../lib/chatApi";
import { clearChatDraft } from "../lib/chatDrafts";
import useEditMessageGeneration from "./useEditMessageGeneration";

vi.mock("../lib/chatApi", () => ({
  streamEditMessage: vi.fn(),
}));

vi.mock("../lib/chatDrafts", () => ({
  clearChatDraft: vi.fn(),
}));

function makeProps(overrides = {}) {
  const initialMessages = [
    { role: "user", text: "Original question" },
    { role: "assistant", text: "Previous answer", sources: [] },
  ];
  let messages = initialMessages;
  const messageCountRef = { current: initialMessages.length };
  const autoSummaryLastMessageCountRef = { current: { "conversation-1": 3 } };
  const streamAbortRef = { current: null };
  const setMessages = vi.fn((next) => {
    messages = typeof next === "function" ? next(messages) : next;
  });
  const props = {
    readOnlyConversation: false,
    editingMessageIndex: 0,
    input: "  Reworded question  ",
    conversationId: "conversation-1",
    userId: 7,
    loading: false,
    messages: initialMessages,
    autoSummaryLastMessageCountRef,
    setError: vi.fn(),
    setRetryableUserMessage: vi.fn(),
    messageCountRef,
    setMessages,
    setInput: vi.fn(),
    setEditingMessageIndex: vi.fn(),
    setLoading: vi.fn(),
    streamAbortRef,
    setConversationId: vi.fn(),
    handleToolEvent: vi.fn(),
    appendToLastMessage: (chunk) => {
      setMessages((prev) =>
        prev.map((message, index) =>
          index === prev.length - 1
            ? { ...message, text: (message.text || "") + chunk }
            : message
        )
      );
    },
    setToolActivity: vi.fn(),
    refreshConversations: vi.fn(),
    showArchivedConversations: false,
    selectedFolderId: "folder-1",
    selectedWorkspaceId: "workspace-1",
    selectedProjectId: "project-1",
    maybeAutoSummarizeConversation: vi.fn(),
    ...overrides,
  };
  return { props, getMessages: () => messages, initialMessages };
}

describe("useEditMessageGeneration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("streams the edited message, refreshes the list, and schedules summary on success", async () => {
    const { props, getMessages } = makeProps();
    streamEditMessage.mockImplementationOnce(async (_id, _index, _text, options) => {
      options.onConversationId("conversation-1");
      options.onToolEvent({ type: "tool_started" });
      options.onSources([{ title: "Reference" }]);
      options.onChunk("Updated ");
      options.onChunk("answer");
      options.onDone();
    });

    const { result } = renderHook(() => useEditMessageGeneration(props));
    await act(async () => {
      await result.current.editMessage();
    });

    expect(streamEditMessage).toHaveBeenCalledWith(
      "conversation-1",
      1,
      "Reworded question",
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(clearChatDraft).toHaveBeenCalledWith(7, "conversation-1");
    expect(props.setError).toHaveBeenCalledWith("");
    expect(props.setRetryableUserMessage).toHaveBeenCalledWith(null);
    expect(props.setInput).toHaveBeenNthCalledWith(1, "");
    expect(props.setEditingMessageIndex).toHaveBeenCalledWith(null);
    expect(props.setLoading).toHaveBeenNthCalledWith(1, true);
    expect(props.setLoading).toHaveBeenLastCalledWith(false);
    expect(props.setConversationId).toHaveBeenCalledWith("conversation-1");
    expect(props.handleToolEvent).toHaveBeenCalledWith({ type: "tool_started" });
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false,
      "folder-1",
      "workspace-1",
      "project-1"
    );
    expect(props.autoSummaryLastMessageCountRef.current["conversation-1"]).toBe(0);
    expect(props.maybeAutoSummarizeConversation).toHaveBeenCalledWith(
      "conversation-1",
      2
    );
    expect(props.streamAbortRef.current).toBe(null);
    expect(getMessages()).toEqual([
      { role: "user", text: "Reworded question" },
      {
        role: "assistant",
        text: "Updated answer",
        time: expect.any(String),
        sources: [{ title: "Reference" }],
      },
    ]);
  });

  it("restores the previous conversation and editing state on a stream error", async () => {
    const { props, getMessages, initialMessages } = makeProps();
    streamEditMessage.mockImplementationOnce(async (_id, _index, _text, options) => {
      options.onChunk("partial response");
      options.onError("temporary failure");
    });

    const { result } = renderHook(() => useEditMessageGeneration(props));
    await act(async () => {
      await result.current.editMessage();
    });

    expect(props.setError).toHaveBeenCalledWith("temporary failure");
    expect(props.setLoading).toHaveBeenLastCalledWith(false);
    expect(props.setToolActivity).toHaveBeenCalledWith(null);
    expect(props.streamAbortRef.current).toBe(null);
    expect(props.setInput).toHaveBeenLastCalledWith("Reworded question");
    expect(props.setEditingMessageIndex).toHaveBeenLastCalledWith(0);
    expect(props.setMessages).toHaveBeenLastCalledWith(initialMessages);
    expect(getMessages()).toEqual(initialMessages);
  });

  it.each([
    ["read-only conversation", { readOnlyConversation: true }],
    ["message is not being edited", { editingMessageIndex: null }],
    ["missing conversation", { conversationId: null }],
    ["empty edited text", { input: "   " }],
    ["already loading", { loading: true }],
    [
      "no user message exists at or before the target index",
      { messages: [{ role: "assistant", text: "Assistant-only" }] },
    ],
  ])("does not start an edit when %s", async (_label, overrides) => {
    const { props } = makeProps(overrides);
    const { result } = renderHook(() => useEditMessageGeneration(props));
    await act(async () => {
      await result.current.editMessage();
    });

    expect(streamEditMessage).not.toHaveBeenCalled();
    expect(props.setMessages).not.toHaveBeenCalled();
    expect(props.setLoading).not.toHaveBeenCalled();
    expect(props.setError).not.toHaveBeenCalled();
  });
});
