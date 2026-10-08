import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useConversationSharing from "./useConversationSharing";

const sharedApi = vi.hoisted(() => ({
  createConversationShare: vi.fn(),
}));

const workspaceApi = vi.hoisted(() => ({
  shareConversationWithWorkspace: vi.fn(),
  unshareConversationFromWorkspace: vi.fn(),
  getWorkspaceSharedConversation: vi.fn(),
}));

vi.mock("../lib/sharedConversationsApi", () => sharedApi);
vi.mock("../lib/workspaceConversationSharesApi", () => workspaceApi);

const buildProps = (overrides = {}) => ({
  conversationId: "conversation-1",
  selectedWorkspaceId: 7,
  loading: false,
  readOnlyConversation: false,
  workspaceShare: null,
  messages: [{ role: "assistant", text: "Welcome" }],
  setShowShareManager: vi.fn(),
  setReadOnlyConversation: vi.fn(),
  setShowWorkspaceComments: vi.fn(),
  setWorkspaceShare: vi.fn(),
  setSelectedWorkspaceId: vi.fn(),
  setConversationId: vi.fn(),
  setConversationSummary: vi.fn(),
  setConversationSummaryUpdatedAt: vi.fn(),
  setSelectedAssistantId: vi.fn(),
  setSelectedFolderId: vi.fn(),
  setSelectedProjectId: vi.fn(),
  setSelectedModel: vi.fn(),
  setMessages: vi.fn(),
  setInput: vi.fn(),
  setEditingMessageIndex: vi.fn(),
  setToast: vi.fn(),
  openConversation: vi.fn(),
  t: vi.fn((key) => key),
  ...overrides,
});

describe("useConversationSharing", () => {
  it("rejects protected public shares with a password shorter than eight characters", async () => {
    const props = buildProps();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(window, "prompt").mockReturnValue("short");

    const { result } = renderHook(() => useConversationSharing(props));

    await act(() => result.current.handleShareConversation());

    expect(props.setToast).toHaveBeenCalledWith({
      message: "sharing.passwordTooShort",
      type: "error",
    });
    expect(sharedApi.createConversationShare).not.toHaveBeenCalled();

    window.confirm.mockRestore();
    window.prompt.mockRestore();
  });

  it("toggles workspace sharing", async () => {
    const props = buildProps();
    workspaceApi.shareConversationWithWorkspace.mockResolvedValue({
      id: 11,
      conversation_id: "conversation-1",
    });

    const { result } = renderHook(() => useConversationSharing(props));

    await act(() => result.current.handleToggleWorkspaceShare());

    expect(workspaceApi.shareConversationWithWorkspace).toHaveBeenCalledWith(
      "conversation-1"
    );
    expect(props.setWorkspaceShare).toHaveBeenCalledWith({
      id: 11,
      conversation_id: "conversation-1",
    });
  });

  it("loads a shared workspace conversation as read-only", async () => {
    const props = buildProps();
    workspaceApi.getWorkspaceSharedConversation.mockResolvedValue({
      conversation_id: "conversation-9",
      messages: [
        {
          role: "user",
          content: "Hi",
          created_at: "2026-10-08T18:00:00Z",
          sources: [],
        },
      ],
    });

    const { result } = renderHook(() => useConversationSharing(props));

    await act(() =>
      result.current.handleOpenWorkspaceSharedConversation(3, 9)
    );

    expect(
      workspaceApi.getWorkspaceSharedConversation
    ).toHaveBeenCalledWith(3, 9);
    expect(props.setReadOnlyConversation).toHaveBeenCalledWith(true);
    expect(props.setSelectedWorkspaceId).toHaveBeenCalledWith(3);
    expect(props.setConversationId).toHaveBeenCalledWith("conversation-9");
    expect(props.setMessages).toHaveBeenCalledWith([
      {
        role: "user",
        text: "Hi",
        time: expect.any(String),
        sources: [],
        feedback: null,
        isBookmarked: false,
      },
    ]);
  });
});
