import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useSendMessageGeneration from "./useSendMessageGeneration";

vi.mock("../lib/chatApi", () => ({
  streamChatMessage: vi.fn(),
}));
vi.mock("../lib/chatDrafts", () => ({
  clearChatDraft: vi.fn(),
}));
vi.mock("../lib/conversationsApi", () => ({
  moveConversationToFolder: vi.fn(),
}));
vi.mock("../lib/projectsApi", () => ({
  moveConversationToProject: vi.fn(),
}));

import { streamChatMessage } from "../lib/chatApi";
import { clearChatDraft } from "../lib/chatDrafts";
import { moveConversationToFolder } from "../lib/conversationsApi";
import { moveConversationToProject } from "../lib/projectsApi";

function makeProps(overrides = {}) {
  let messages = [];
  const messageCountRef = { current: 0 };
  const streamAbortRef = { current: null };
  const setMessages = vi.fn((next) => {
    messages = typeof next === "function" ? next(messages) : next;
  });
  const editMessage = vi.fn();
  const props = {
    readOnlyConversation: false,
    editingMessageIndex: null,
    editMessage,
    input: "  Check this file  ",
    chatAttachments: [{ id: 7 }],
    userId: 4,
    conversationId: null,
    selectedAssistantId: 12,
    selectedWorkspaceId: 3,
    selectedProjectId: null,
    selectedFolderId: null,
    selectedModel: "model-1",
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
    resetChatAttachments: vi.fn(),
    setError: vi.fn(),
    setRetryableUserMessage: vi.fn(),
    setToolActivity: vi.fn(),
    messageCountRef,
    setMessages,
    setInput: vi.fn(),
    setLoading: vi.fn(),
    streamAbortRef,
    setConversationId: vi.fn(),
    setToast: vi.fn(),
    setActiveConversationTitle: vi.fn(),
    refreshConversations: vi.fn(),
    showArchivedConversations: false,
    maybeAutoGenerateConversationTitle: vi.fn(),
    maybeAutoSummarizeConversation: vi.fn(),
    messages,
    t: (key) => key,
    ...overrides,
  };
  return { props, getMessages: () => messages, editMessage };
}

describe("useSendMessageGeneration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.documentElement.lang = "en";
  });

  it("sends a message, streams sources and chunks, and finalizes a new conversation", async () => {
    const { props, getMessages } = makeProps();
    streamChatMessage.mockImplementationOnce(async (_text, _id, _assistantId, options) => {
      await options.onConversationId("conversation-2");
      options.onToolEvent({ type: "tool_started" });
      options.onSources([{ title: "Reference" }]);
      options.onChunk("Hello ");
      options.onChunk("world");
      await options.onDone();
    });

    const { result } = renderHook(() => useSendMessageGeneration(props));
    await act(async () => {
      await result.current.sendMessage();
    });

    expect(streamChatMessage).toHaveBeenCalledWith(
      "Check this file",
      null,
      12,
      expect.objectContaining({
        workspaceId: 3,
        projectId: null,
        model: "model-1",
        fileIds: [7],
        signal: expect.any(AbortSignal),
      })
    );
    expect(clearChatDraft).toHaveBeenCalledWith(4, null);
    expect(props.setInput).toHaveBeenCalledWith("");
    expect(props.setLoading).toHaveBeenNthCalledWith(1, true);
    expect(props.setLoading).toHaveBeenLastCalledWith(false);
    expect(props.handleToolEvent).toHaveBeenCalledWith({ type: "tool_started" });
    expect(props.setConversationId).toHaveBeenCalledWith("conversation-2");
    expect(props.resetChatAttachments).toHaveBeenCalledTimes(1);
    expect(props.setActiveConversationTitle).toHaveBeenCalledWith("Check this file");
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, 3, null);
    expect(props.maybeAutoGenerateConversationTitle).toHaveBeenCalledWith("conversation-2");
    expect(props.maybeAutoSummarizeConversation).toHaveBeenCalledWith("conversation-2", 2);
    expect(props.streamAbortRef.current).toBe(null);
    expect(getMessages()).toEqual([
      { role: "user", text: "Check this file", time: expect.any(String) },
      {
        role: "assistant",
        text: "Hello world",
        time: expect.any(String),
        feedback: null,
        sources: [{ title: "Reference" }],
      },
    ]);
    expect(props.setRetryableUserMessage).toHaveBeenLastCalledWith(null);
  });

  it("uses the localized fallback prompt when only files are attached", async () => {
    document.documentElement.lang = "ar";
    const { props } = makeProps({ input: " ", chatAttachments: [{ id: 19 }], conversationId: "conversation-1" });
    streamChatMessage.mockImplementationOnce(async (_text, _id, _assistantId, options) => {
      options.onError("temporary failure");
    });

    const { result } = renderHook(() => useSendMessageGeneration(props));
    await act(async () => {
      await result.current.sendMessage();
    });

    expect(streamChatMessage).toHaveBeenCalledWith(
      "أرسل لي الملف المرفق وحلله.",
      "conversation-1",
      12,
      expect.objectContaining({ fileIds: [19] })
    );
    expect(props.setRetryableUserMessage).toHaveBeenCalledWith({
      conversationId: "conversation-1",
      text: "أرسل لي الملف المرفق وحلله.",
      fileIds: [19],
      assistantId: 12,
      workspaceId: 3,
      projectId: null,
      folderId: null,
      model: "model-1",
      retryMode: "send",
      isNewConversation: false,
    });
  });

  it("marks a streamed failure as regenerate-ready because the user message was persisted", async () => {
    const { props } = makeProps({ conversationId: "conversation-1" });
    streamChatMessage.mockImplementationOnce(async (_text, _id, _assistantId, options) => {
      options.onError("provider timed out", { kind: "stream", messagePersisted: true });
    });

    const { result } = renderHook(() => useSendMessageGeneration(props));
    await act(async () => {
      await result.current.sendMessage();
    });

    expect(props.setRetryableUserMessage).toHaveBeenLastCalledWith({
      conversationId: "conversation-1",
      text: "Check this file",
      fileIds: [7],
      assistantId: 12,
      workspaceId: 3,
      projectId: null,
      folderId: null,
      model: "model-1",
      retryMode: "regenerate",
      isNewConversation: false,
    });
  });

  it("rolls back an empty placeholder and restores retry state when generation fails", async () => {
    const { props, getMessages } = makeProps({ conversationId: "conversation-1" });
    streamChatMessage.mockImplementationOnce(async (_text, _id, _assistantId, options) => {
      options.onError("temporary failure");
    });

    const { result } = renderHook(() => useSendMessageGeneration(props));
    await act(async () => {
      await result.current.sendMessage();
    });

    expect(props.setError).toHaveBeenCalledWith("temporary failure");
    expect(props.setLoading).toHaveBeenLastCalledWith(false);
    expect(props.messageCountRef.current).toBe(1);
    expect(props.streamAbortRef.current).toBe(null);
    expect(getMessages()).toEqual([
      { role: "user", text: "Check this file", time: expect.any(String) },
    ]);
    expect(props.setRetryableUserMessage).toHaveBeenLastCalledWith({
      conversationId: "conversation-1",
      text: "Check this file",
      fileIds: [7],
      assistantId: 12,
      workspaceId: 3,
      projectId: null,
      folderId: null,
      model: "model-1",
      retryMode: "send",
      isNewConversation: false,
    });
  });

  it("moves a new conversation into the selected folder and reports a move failure", async () => {
    const { props } = makeProps({ selectedFolderId: "folder-5" });
    moveConversationToFolder.mockRejectedValueOnce(new Error("move failed"));
    streamChatMessage.mockImplementationOnce(async (_text, _id, _assistantId, options) => {
      await options.onConversationId("conversation-3");
      await options.onDone();
    });

    const { result } = renderHook(() => useSendMessageGeneration(props));
    await act(async () => {
      await result.current.sendMessage();
    });

    expect(moveConversationToFolder).toHaveBeenCalledWith("conversation-3", "folder-5");
    expect(moveConversationToProject).not.toHaveBeenCalled();
    expect(props.setToast).toHaveBeenCalledWith({
      message: "app.conversationMoveError",
      type: "error",
    });
  });

  it("prefers project placement if both a project and folder are selected", async () => {
    const { props } = makeProps({ selectedProjectId: "project-8", selectedFolderId: "folder-5" });
    streamChatMessage.mockImplementationOnce(async (_text, _id, _assistantId, options) => {
      await options.onConversationId("conversation-8");
      await options.onDone();
    });

    const { result } = renderHook(() => useSendMessageGeneration(props));
    await act(async () => {
      await result.current.sendMessage();
    });

    expect(moveConversationToProject).toHaveBeenCalledWith("conversation-8", "project-8");
    expect(moveConversationToFolder).not.toHaveBeenCalled();
  });

  it("delegates to editing and does not send a new message while editing", async () => {
    const { props, editMessage } = makeProps({ editingMessageIndex: 0 });
    const { result } = renderHook(() => useSendMessageGeneration(props));

    await act(async () => {
      await result.current.sendMessage();
    });

    expect(editMessage).toHaveBeenCalledTimes(1);
    expect(streamChatMessage).not.toHaveBeenCalled();
    expect(props.setMessages).not.toHaveBeenCalled();
  });

  it.each([
    ["read-only conversation", { readOnlyConversation: true }],
    ["empty text and no files", { input: " ", chatAttachments: [] }],
  ])("does not start generation when %s", async (_label, overrides) => {
    const { props } = makeProps(overrides);
    const { result } = renderHook(() => useSendMessageGeneration(props));

    await act(async () => {
      await result.current.sendMessage();
    });

    expect(streamChatMessage).not.toHaveBeenCalled();
    expect(props.setMessages).not.toHaveBeenCalled();
    expect(props.setLoading).not.toHaveBeenCalled();
  });
});
