import { act, renderHook } from "@testing-library/react";
import { useRef, useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useMessageSending from "./useMessageSending";

const mocks = vi.hoisted(() => ({
  streamChatMessage: vi.fn(),
  clearChatDraft: vi.fn(),
  moveConversationToFolder: vi.fn(),
  moveConversationToProject: vi.fn(),
}));

vi.mock("../lib/chatApi", () => ({
  streamChatMessage: mocks.streamChatMessage,
}));

vi.mock("../lib/chatDrafts", () => ({
  clearChatDraft: mocks.clearChatDraft,
}));

vi.mock("../lib/conversationsApi", () => ({
  moveConversationToFolder: mocks.moveConversationToFolder,
}));

vi.mock("../lib/projectsApi", () => ({
  moveConversationToProject: mocks.moveConversationToProject,
}));

function setup(overrides = {}) {
  const deps = {
    readOnlyConversation: false,
    editingMessageIndex: null,
    editMessage: vi.fn().mockResolvedValue(undefined),
    initialInput: "Question",
    chatAttachments: [],
    currentUser: { id: 7 },
    conversationId: null,
    selectedAssistantId: null,
    selectedWorkspaceId: null,
    selectedProjectId: null,
    selectedFolderId: null,
    selectedModel: "model-a",
    handleToolEvent: vi.fn(),
    setConversationId: vi.fn(),
    setError: vi.fn(),
    setRetryableUserMessage: vi.fn(),
    setToolActivity: vi.fn(),
    setToast: vi.fn(),
    resetChatAttachments: vi.fn(),
    setActiveConversationTitle: vi.fn(),
    refreshConversations: vi.fn(),
    showArchivedConversations: false,
    maybeAutoGenerateConversationTitle: vi.fn().mockResolvedValue(undefined),
    maybeAutoSummarizeConversation: vi.fn(),
    t: (key) => key,
    ...overrides,
  };
  const hook = renderHook(() => {
    const [messages, setMessages] = useState([
      { role: "assistant", text: "Welcome", time: "now" },
    ]);
    const [input, setInput] = useState(deps.initialInput);
    const [loading, setLoading] = useState(false);
    const messageCountRef = useRef(messages.length);
    const streamAbortRef = useRef(null);
    const appendToLastMessage = (chunk) => {
      setMessages((current) =>
        current.map((message, index) =>
          index === current.length - 1
            ? { ...message, text: message.text + chunk }
            : message
        )
      );
    };
    const actions = useMessageSending({
      ...deps,
      input,
      messages,
      setMessages,
      setInput,
      setLoading,
      messageCountRef,
      streamAbortRef,
      appendToLastMessage,
    });
    return {
      ...actions,
      messages,
      input,
      loading,
      messageCountRef,
      streamAbortRef,
    };
  });
  return { ...hook, deps };
}

describe("useMessageSending", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("streams a new message and applies completion callbacks", async () => {
    mocks.streamChatMessage.mockImplementationOnce(
      async (_text, _conversationId, _assistantId, callbacks) => {
        await callbacks.onConversationId(101);
        callbacks.onSources([{ id: "source-1" }]);
        callbacks.onChunk("Answer");
        await callbacks.onDone();
      }
    );
    const { result, deps } = setup();

    await act(async () => {
      await result.current.sendMessage();
    });

    expect(mocks.clearChatDraft).toHaveBeenCalledWith(7, null);
    expect(mocks.streamChatMessage).toHaveBeenCalledWith(
      "Question",
      null,
      null,
      expect.objectContaining({
        workspaceId: null,
        projectId: null,
        model: "model-a",
        fileIds: [],
      })
    );
    expect(result.current.messages).toEqual([
      { role: "assistant", text: "Welcome", time: "now" },
      expect.objectContaining({ role: "user", text: "Question" }),
      expect.objectContaining({
        role: "assistant",
        text: "Answer",
        sources: [{ id: "source-1" }],
      }),
    ]);
    expect(result.current.loading).toBe(false);
    expect(result.current.input).toBe("");
    expect(result.current.streamAbortRef.current).toBeNull();
    expect(deps.setConversationId).toHaveBeenCalledWith(101);
    expect(deps.resetChatAttachments).toHaveBeenCalledOnce();
    expect(deps.maybeAutoGenerateConversationTitle).toHaveBeenCalledWith(101);
    expect(deps.maybeAutoSummarizeConversation).toHaveBeenCalledWith(101, 3);
  });

  it("restores the message list and exposes retry for an existing conversation after stream failure", async () => {
    mocks.streamChatMessage.mockImplementationOnce(
      async (_text, _conversationId, _assistantId, callbacks) => {
        callbacks.onError("connection lost");
      }
    );
    const { result, deps } = setup({ conversationId: "conv-1" });

    await act(async () => {
      await result.current.sendMessage();
    });

    expect(deps.setError).toHaveBeenCalledWith("connection lost");
    expect(deps.setRetryableUserMessage).toHaveBeenCalledWith({
      conversationId: "conv-1",
      text: "Question",
    });
    expect(result.current.messages).toEqual([
      { role: "assistant", text: "Welcome", time: "now" },
      expect.objectContaining({ role: "user", text: "Question" }),
    ]);
    expect(result.current.loading).toBe(false);
    expect(result.current.streamAbortRef.current).toBeNull();
    expect(deps.resetChatAttachments).not.toHaveBeenCalled();
  });

  it("does not send an empty message without attachments", async () => {
    const { result } = setup({ initialInput: "   " });

    await act(async () => {
      await result.current.sendMessage();
    });

    expect(mocks.streamChatMessage).not.toHaveBeenCalled();
    expect(mocks.clearChatDraft).not.toHaveBeenCalled();
    expect(result.current.messages).toEqual([
      { role: "assistant", text: "Welcome", time: "now" },
    ]);
  });

  it("does not send a message in a read-only conversation", async () => {
    const { result } = setup({ readOnlyConversation: true });

    await act(async () => {
      await result.current.sendMessage();
    });

    expect(mocks.streamChatMessage).not.toHaveBeenCalled();
  });

  it("delegates to editMessage while editing instead of starting a new stream", async () => {
    const { result, deps } = setup({ editingMessageIndex: 1 });

    await act(async () => {
      await result.current.sendMessage();
    });

    expect(deps.editMessage).toHaveBeenCalledOnce();
    expect(mocks.streamChatMessage).not.toHaveBeenCalled();
  });
});
