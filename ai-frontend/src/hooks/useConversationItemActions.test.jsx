import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useConversationItemActions from "./useConversationItemActions";

vi.mock("../lib/conversationsApi", () => ({
  deleteConversation: vi.fn(),
  toggleArchiveConversation: vi.fn(),
  togglePinConversation: vi.fn(),
  toggleTrashConversation: vi.fn(),
}));

import {
  deleteConversation,
  toggleArchiveConversation,
  togglePinConversation,
  toggleTrashConversation,
} from "../lib/conversationsApi";

const baseProps = () => ({
  conversationId: 7,
  conversationSearch: "hello",
  refreshConversations: vi.fn(() => Promise.resolve()),
  selectedFolderId: null,
  selectedProjectId: null,
  selectedWorkspaceId: null,
  setToast: vi.fn(),
  showArchivedConversations: false,
  showTrashConversations: false,
  startNewChat: vi.fn(),
  t: (key) => key,
});

describe("useConversationItemActions", () => {
  it("pins a conversation and refreshes the current list", async () => {
    const props = baseProps();
    togglePinConversation.mockResolvedValueOnce({});

    const { result } = renderHook(() => useConversationItemActions(props));
    await result.current.handleTogglePinConversation(11);

    expect(togglePinConversation).toHaveBeenCalledWith(11);
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, null, null);
  });

  it("archives the active conversation by starting a fresh chat", async () => {
    const props = baseProps();
    toggleArchiveConversation.mockResolvedValueOnce({ is_archived: true });

    const { result } = renderHook(() => useConversationItemActions(props));
    await result.current.handleToggleArchiveConversation(7);

    expect(props.startNewChat).toHaveBeenCalledTimes(1);
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, null, null);
  });

  it("deletes from trash, while using trash for non-trash conversations", async () => {
    const props = baseProps();
    props.showTrashConversations = true;
    deleteConversation.mockResolvedValueOnce({});
    toggleTrashConversation.mockResolvedValueOnce({});

    const { result, rerender } = renderHook((p) => useConversationItemActions(p), {
      initialProps: props,
    });
    await result.current.handleDeleteConversation(7);

    expect(deleteConversation).toHaveBeenCalledWith(7);
    expect(toggleTrashConversation).not.toHaveBeenCalled();
    expect(props.startNewChat).toHaveBeenCalledTimes(1);

    props.showTrashConversations = false;
    rerender(props);
    await result.current.handleDeleteConversation(8);

    expect(toggleTrashConversation).toHaveBeenCalledWith(8);
  });
});
