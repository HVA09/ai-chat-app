import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useWorkspaceConversationSharing from "./useWorkspaceConversationSharing";

const createProps = () => ({
  conversationId: 7,
  selectedWorkspaceId: 3,
  workspaceShare: null,
  loading: false,
  readOnlyConversation: false,
  openConversation: vi.fn().mockResolvedValue(undefined),
  getWorkspaceSharedConversation: vi.fn().mockResolvedValue({
    conversation_id: 19,
    messages: [
      {
        role: "user",
        content: "Hello",
        created_at: "2026-10-08T10:00:00Z",
        sources: [{ title: "source" }],
      },
    ],
  }),
  shareConversationWithWorkspace: vi.fn().mockResolvedValue({ id: 11 }),
  unshareConversationFromWorkspace: vi.fn().mockResolvedValue(undefined),
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
  setError: vi.fn(),
  setToast: vi.fn(),
  t: (key) => key,
});

describe("useWorkspaceConversationSharing", () => {
  it("opens a shared workspace conversation as read-only", async () => {
    const props = createProps();
    const { result } = renderHook(() => useWorkspaceConversationSharing(props));

    await result.current.handleOpenWorkspaceSharedConversation(3, 19);

    expect(props.getWorkspaceSharedConversation).toHaveBeenCalledWith(3, 19);
    expect(props.setReadOnlyConversation).toHaveBeenCalledWith(true);
    expect(props.setSelectedWorkspaceId).toHaveBeenCalledWith(3);
    expect(props.setConversationId).toHaveBeenCalledWith(19);
    expect(props.setMessages).toHaveBeenCalledWith([
      expect.objectContaining({
        role: "user",
        text: "Hello",
        sources: [{ title: "source" }],
      }),
    ]);
  });

  it("shares and unshares the active conversation", async () => {
    const props = createProps();
    const { result, rerender } = renderHook(
      (hookProps) => useWorkspaceConversationSharing(hookProps),
      { initialProps: props }
    );

    await result.current.handleToggleWorkspaceShare();
    expect(props.shareConversationWithWorkspace).toHaveBeenCalledWith(7);
    expect(props.setWorkspaceShare).toHaveBeenCalledWith({ id: 11 });

    const unshareProps = { ...props, workspaceShare: { id: 11 } };
    rerender(unshareProps);
    await result.current.handleToggleWorkspaceShare();
    expect(unshareProps.unshareConversationFromWorkspace).toHaveBeenCalledWith(7);
    expect(unshareProps.setWorkspaceShare).toHaveBeenCalledWith(null);
  });

  it("rejects an invalid duplication target", async () => {
    const props = createProps();
    const { result } = renderHook(() => useWorkspaceConversationSharing(props));

    await result.current.handleDuplicatedWorkspaceConversation(null);

    expect(props.openConversation).not.toHaveBeenCalled();
    expect(props.setToast).toHaveBeenCalledWith({
      message: "workspaceSharing.duplicateError",
      type: "error",
    });
  });
});
