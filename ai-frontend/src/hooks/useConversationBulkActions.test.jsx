import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useConversationBulkActions from "./useConversationBulkActions";

vi.mock("../lib/conversationsApi", () => ({
  deleteConversation: vi.fn(),
  exportConversations: vi.fn(),
  moveConversationToFolder: vi.fn(),
  toggleArchiveConversation: vi.fn(),
  toggleTrashConversation: vi.fn(),
}));

import {
  deleteConversation,
  exportConversations,
  moveConversationToFolder,
  toggleArchiveConversation,
  toggleTrashConversation,
} from "../lib/conversationsApi";

describe("useConversationBulkActions", () => {
  const baseProps = () => ({
    conversationId: 2,
    refreshConversations: vi.fn().mockResolvedValue(undefined),
    selectedConversationIds: [2, 3],
    selectedFolderId: 5,
    selectedProjectId: 6,
    selectedWorkspaceId: 7,
    setSelectedConversationIds: vi.fn(),
    setToast: vi.fn(),
    showArchivedConversations: false,
    showTrashConversations: false,
    startNewChat: vi.fn(),
    t: (key, vars) => key + ":" + (vars?.count ?? ""),
  });

  it("archives selected conversations and refreshes the visible list", async () => {
    toggleArchiveConversation.mockResolvedValue({});
    const props = baseProps();
    const { result } = renderHook(() => useConversationBulkActions(props));

    await result.current.handleBulkArchive();

    expect(toggleArchiveConversation).toHaveBeenCalledTimes(2);
    expect(props.startNewChat).toHaveBeenCalled();
    expect(props.setSelectedConversationIds).toHaveBeenCalledWith([]);
    expect(props.refreshConversations).toHaveBeenCalledWith(false, 5, 7, 6);
  });

  it("exports selected conversations and clears the selection", async () => {
    exportConversations.mockResolvedValue(undefined);
    const props = baseProps();
    const { result } = renderHook(() => useConversationBulkActions(props));

    await result.current.handleBulkExport();

    expect(exportConversations).toHaveBeenCalledWith([2, 3]);
    expect(props.setSelectedConversationIds).toHaveBeenCalledWith([]);
  });

  it("moves selected conversations to the requested folder", async () => {
    moveConversationToFolder.mockResolvedValue({});
    const props = baseProps();
    const { result } = renderHook(() => useConversationBulkActions(props));

    await result.current.handleBulkMoveToFolder("9");

    expect(moveConversationToFolder).toHaveBeenCalledWith(2, 9);
    expect(moveConversationToFolder).toHaveBeenCalledWith(3, 9);
    expect(props.startNewChat).toHaveBeenCalled();
  });

  it("uses permanent deletion in trash view", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const props = { ...baseProps(), showTrashConversations: true };
    deleteConversation.mockResolvedValue(undefined);
    const { result } = renderHook(() => useConversationBulkActions(props));

    await result.current.handleBulkDelete();

    expect(deleteConversation).toHaveBeenCalledTimes(2);
    expect(toggleTrashConversation).not.toHaveBeenCalled();
    vi.restoreAllMocks();
  });

  it("does not delete without confirmation", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const props = baseProps();
    const { result } = renderHook(() => useConversationBulkActions(props));

    await result.current.handleBulkDelete();

    expect(toggleTrashConversation).not.toHaveBeenCalled();
    expect(deleteConversation).not.toHaveBeenCalled();
    vi.restoreAllMocks();
  });
});
