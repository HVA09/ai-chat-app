import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useOpenConversation from "./useOpenConversation";

const getConversation = vi.fn();
const listConversationBranches = vi.fn();
const getConversationWorkspaceShare = vi.fn();

vi.mock("../lib/conversationsApi", () => ({
  getConversation: (...args) => getConversation(...args),
  listConversationBranches: (...args) => listConversationBranches(...args),
}));

vi.mock("../lib/workspaceConversationSharesApi", () => ({
  getConversationWorkspaceShare: (...args) => getConversationWorkspaceShare(...args),
}));

vi.mock("../lib/errors", () => ({
  getErrorMessage: vi.fn((error, fallback) => error?.message || fallback),
}));

function createProps() {
  return {
    aiModels: [{ id: "default-model", is_default: true }],
    setConversationId: vi.fn(),
    setActiveConversationTitle: vi.fn(),
    setParentConversationId: vi.fn(),
    setConversationBranches: vi.fn(),
    setConversationSummary: vi.fn(),
    setConversationSummaryUpdatedAt: vi.fn(),
    setSelectedAssistantId: vi.fn(),
    setSelectedWorkspaceId: vi.fn(),
    setSelectedFolderId: vi.fn(),
    setSelectedProjectId: vi.fn(),
    setSelectedModel: vi.fn(),
    setWorkspaceShare: vi.fn(),
    setMessages: vi.fn(),
    setSelectedConversationIds: vi.fn(),
    setShowShareManager: vi.fn(),
    setReadOnlyConversation: vi.fn(),
    setShowWorkspaceComments: vi.fn(),
    setError: vi.fn(),
    setToast: vi.fn(),
    setInput: vi.fn(),
    resetChatAttachments: vi.fn(),
    setEditingMessageIndex: vi.fn(),
    setRetryableUserMessage: vi.fn(),
    messageCountRef: { current: 0 },
    autoSummaryLastMessageCountRef: { current: {} },
    t: (key) => key,
  };
}

describe("useOpenConversation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getConversation.mockResolvedValue({
      id: 7,
      title: "Loaded chat",
      parent_conversation_id: 3,
      messages: [
        {
          role: "user",
          content: "Hello",
          created_at: "2026-10-07T12:00:00Z",
          sources: [],
          feedback: null,
          is_bookmarked: false,
        },
      ],
      summary: "Summary",
      summary_updated_at: "2026-10-07T12:01:00Z",
      assistant_id: 4,
      workspace_id: 5,
      folder_id: 6,
      project_id: 8,
      ai_model: "model-a",
    });
    listConversationBranches.mockResolvedValue([{ id: 10 }]);
    getConversationWorkspaceShare.mockResolvedValue({ id: 20 });
  });

  it("loads the conversation and applies its state", async () => {
    const props = createProps();
    const { result } = renderHook(() => useOpenConversation(props));

    await result.current.openConversation(7);

    expect(getConversation).toHaveBeenCalledWith(7);
    expect(props.setConversationId).toHaveBeenCalledWith(7);
    expect(props.setActiveConversationTitle).toHaveBeenCalledWith("Loaded chat");
    expect(props.setParentConversationId).toHaveBeenCalledWith(3);
    expect(props.setConversationBranches).toHaveBeenCalledWith([{ id: 10 }]);
    expect(props.setConversationSummary).toHaveBeenCalledWith("Summary");
    expect(props.setSelectedAssistantId).toHaveBeenCalledWith(4);
    expect(props.setSelectedWorkspaceId).toHaveBeenCalledWith(5);
    expect(props.setSelectedFolderId).toHaveBeenCalledWith(6);
    expect(props.setSelectedProjectId).toHaveBeenCalledWith(8);
    expect(props.setSelectedModel).toHaveBeenCalledWith("model-a");
    expect(props.setWorkspaceShare).toHaveBeenCalledWith({ id: 20 });
    expect(props.setMessages).toHaveBeenCalledWith([
      {
        role: "user",
        text: "Hello",
        time: expect.any(String),
        sources: [],
        feedback: null,
        isBookmarked: false,
      },
    ]);
    expect(props.messageCountRef.current).toBe(1);
    expect(props.autoSummaryLastMessageCountRef.current[7]).toBe(1);
  });

  it("ignores stale responses when a newer conversation opens", async () => {
    let resolveFirst;
    let resolveSecond;
    getConversation
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveFirst = resolve;
          })
      )
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveSecond = resolve;
          })
      );

    const props = createProps();
    const { result } = renderHook(() => useOpenConversation(props));

    const first = result.current.openConversation(1);
    const second = result.current.openConversation(2);

    resolveSecond({ id: 2, title: "Second", messages: [] });
    await second;

    resolveFirst({ id: 1, title: "First", messages: [] });
    await first;

    expect(props.setConversationId).toHaveBeenLastCalledWith(2);
    expect(props.setActiveConversationTitle).toHaveBeenLastCalledWith("Second");
    expect(props.setActiveConversationTitle).not.toHaveBeenCalledWith("First");
  });
});
