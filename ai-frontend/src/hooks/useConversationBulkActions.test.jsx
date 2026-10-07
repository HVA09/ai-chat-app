import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  deleteConversation,
  exportConversations,
  moveConversationToFolder,
  toggleArchiveConversation,
  toggleTrashConversation,
} from "../lib/conversationsApi";
import useConversationBulkActions from "./useConversationBulkActions";

vi.mock("../lib/conversationsApi", () => ({
  deleteConversation: vi.fn(),
  exportConversations: vi.fn(),
  moveConversationToFolder: vi.fn(),
  toggleArchiveConversation: vi.fn(),
  toggleTrashConversation: vi.fn(),
}));

afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

function createProps(overrides = {}) {
  return {
    selectedConversationIds: [1, 2],
    conversationId: 2,
    showArchivedConversations: false,
    showTrashConversations: false,
    selectedFolderId: null,
    selectedWorkspaceId: 10,
    selectedProjectId: null,
    refreshConversations: vi.fn(),
    setSelectedConversationIds: vi.fn(),
    startNewChat: vi.fn(),
    setToast: vi.fn(),
    t: vi.fn((key, values) => key + ":" + (values?.count ?? "")),
    ...overrides,
  };
}

describe("useConversationBulkActions", () => {
  it("archives selected conversations and resets the active one", async () => {
    toggleArchiveConversation.mockResolvedValue({});
    const props = createProps();
    const { result } = renderHook(() => useConversationBulkActions(props));

    await result.current.handleBulkArchive();

    expect(toggleArchiveConversation).toHaveBeenCalledTimes(2);
    expect(props.startNewChat).toHaveBeenCalled();
    expect(props.setSelectedConversationIds).toHaveBeenCalledWith([]);
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, 10, null);
  });

  it("deletes from trash directly and uses trash toggle otherwise", async () => {
    toggleTrashConversation.mockResolvedValue({});
    const normalProps = createProps();
    const { result: normal } = renderHook(() =>
      useConversationBulkActions(normalProps)
    );
    vi.spyOn(window, "confirm").mockReturnValue(true);
    await normal.current.handleBulkDelete();
    expect(toggleTrashConversation).toHaveBeenCalledTimes(2);

    deleteConversation.mockResolvedValue({});
    const trashProps = createProps({ showTrashConversations: true });
    const { result: trash } = renderHook(() =>
      useConversationBulkActions(trashProps)
    );
    await trash.current.handleBulkDelete();
    expect(deleteConversation).toHaveBeenCalledTimes(2);
  });

  it("exports selected conversations and clears selection", async () => {
    exportConversations.mockResolvedValue({});
    const props = createProps();
    const { result } = renderHook(() => useConversationBulkActions(props));

    await result.current.handleBulkExport();

    expect(exportConversations).toHaveBeenCalledWith([1, 2]);
    expect(props.setSelectedConversationIds).toHaveBeenCalledWith([]);
    expect(props.setToast).toHaveBeenCalledWith({
      message: "app.bulkExportSuccess:",
      type: "success",
    });
  });

  it("moves selected conversations to a folder and resets the active conversation when it changes folder", async () => {
    moveConversationToFolder.mockResolvedValue({});
    const props = createProps({ selectedFolderId: 4 });
    const { result } = renderHook(() => useConversationBulkActions(props));

    await result.current.handleBulkMoveToFolder("__none__");

    expect(moveConversationToFolder).toHaveBeenCalledWith(1, null);
    expect(moveConversationToFolder).toHaveBeenCalledWith(2, null);
    expect(props.startNewChat).toHaveBeenCalled();
    expect(props.refreshConversations).toHaveBeenCalledWith(false, 4, 10, null);
  });

  it("does not delete when the user cancels", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const props = createProps();
    const { result } = renderHook(() => useConversationBulkActions(props));

    await result.current.handleBulkDelete();

    expect(toggleTrashConversation).not.toHaveBeenCalled();
  });
});
