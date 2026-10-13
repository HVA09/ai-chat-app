import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useConversationItemActions from "./useConversationItemActions";

vi.mock("../lib/conversationsApi", () => ({
  deleteConversation: vi.fn(),
  duplicateConversation: vi.fn(),
  renameConversation: vi.fn(),
  toggleArchiveConversation: vi.fn(),
  togglePinConversation: vi.fn(),
  toggleTrashConversation: vi.fn(),
}));

import {
  deleteConversation,
  duplicateConversation,
  renameConversation,
  toggleArchiveConversation,
  togglePinConversation,
  toggleTrashConversation,
} from "../lib/conversationsApi";

const baseProps = () => ({
  conversationId: 7,
  conversationSearch: "hello",
  openConversation: vi.fn(() => Promise.resolve()),
  refreshConversations: vi.fn(() => Promise.resolve()),
  selectedFolderId: null,
  selectedProjectId: null,
  selectedTagId: 9,
  selectedWorkspaceId: null,
  setToast: vi.fn(),
  showArchivedConversations: false,
  showTrashConversations: false,
  startNewChat: vi.fn(),
  t: (key) => key,
});

describe("useConversationItemActions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renames a conversation and refreshes", async () => {
    const props = baseProps();
    renameConversation.mockResolvedValueOnce({});
    const { result } = renderHook(() => useConversationItemActions(props));

    await result.current.handleRenameConversation(11, "Renamed");

    expect(renameConversation).toHaveBeenCalledWith(11, "Renamed");
    expect(props.refreshConversations).toHaveBeenCalledWith();
  });

  it("duplicates a conversation, refreshes the current filters, and opens the new copy", async () => {
    const props = baseProps();
    duplicateConversation.mockResolvedValueOnce({ id: 99 });
    const { result } = renderHook(() => useConversationItemActions(props));

    await result.current.handleDuplicateConversation(11);

    expect(duplicateConversation).toHaveBeenCalledWith(11);
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false, null, null, null, "hello", false, 9
    );
    expect(props.openConversation).toHaveBeenCalledWith(99);
    expect(props.setToast).toHaveBeenCalledWith({
      message: "app.duplicateConversationSuccess",
      type: "success",
    });
  });

  it("reports a duplicate failure without opening a conversation", async () => {
    duplicateConversation.mockRejectedValueOnce({
      response: { data: { detail: "duplicate denied" } },
    });
    const props = baseProps();
    const { result } = renderHook(() => useConversationItemActions(props));

    await result.current.handleDuplicateConversation(11);

    expect(props.setToast).toHaveBeenCalledWith({
      message: "duplicate denied",
      type: "error",
    });
    expect(props.refreshConversations).not.toHaveBeenCalled();
    expect(props.openConversation).not.toHaveBeenCalled();
  });

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

    const { result, rerender } = renderHook(
      (currentProps) => useConversationItemActions(currentProps),
      { initialProps: props }
    );

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
