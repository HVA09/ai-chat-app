import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createFolder,
  deleteFolder,
  listFolders,
  moveFolder,
  renameFolder,
} from "../lib/foldersApi";
import useFolderManagement from "./useFolderManagement";

vi.mock("../lib/foldersApi", () => ({
  createFolder: vi.fn(),
  deleteFolder: vi.fn(),
  listFolders: vi.fn(),
  moveFolder: vi.fn(),
  renameFolder: vi.fn(),
}));

vi.mock("../lib/errors", () => ({
  getErrorMessage: vi.fn((_error, fallback) => fallback),
}));

function createProps(overrides = {}) {
  return {
    selectedWorkspaceId: 3,
    selectedFolderId: 5,
    selectedProjectId: 8,
    showArchivedConversations: false,
    conversationId: 42,
    setFolders: vi.fn(),
    setSelectedFolderId: vi.fn(),
    setSelectedProjectId: vi.fn(),
    startNewChat: vi.fn(),
    refreshConversations: vi.fn().mockResolvedValue(undefined),
    maybeAutoSummarizeConversation: vi.fn(),
    messageCountRef: { current: 12 },
    setToast: vi.fn(),
    t: (key) => key,
    ...overrides,
  };
}

describe("useFolderManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listFolders.mockResolvedValue([]);
    createFolder.mockResolvedValue({ id: 19, name: "Research" });
    renameFolder.mockResolvedValue({});
    moveFolder.mockResolvedValue({});
    deleteFolder.mockResolvedValue({});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loads folders for the selected workspace", async () => {
    const folders = [{ id: 5, name: "Research" }];
    listFolders.mockResolvedValueOnce(folders);
    const props = createProps();
    const { result } = renderHook(() => useFolderManagement(props));

    await act(async () => {
      await result.current.refreshFolders();
    });

    expect(listFolders).toHaveBeenCalledWith(3);
    expect(props.setFolders).toHaveBeenCalledWith(folders);
  });

  it("creates and selects a folder, then refreshes its conversation list", async () => {
    vi.spyOn(window, "prompt").mockReturnValue("  Research  ");
    const props = createProps();
    const { result } = renderHook(() => useFolderManagement(props));

    await act(async () => {
      await result.current.handleCreateFolder();
    });

    expect(createFolder).toHaveBeenCalledWith("Research", 3);
    expect(props.setFolders).toHaveBeenCalledWith([]);
    expect(props.setSelectedFolderId).toHaveBeenCalledWith(19);
    expect(props.startNewChat).toHaveBeenCalledOnce();
    expect(props.refreshConversations).toHaveBeenCalledWith(false, 19, 3, null);
  });

  it("does not create a folder when the prompt is cancelled or blank", async () => {
    vi.spyOn(window, "prompt").mockReturnValue("  ");
    const props = createProps();
    const { result } = renderHook(() => useFolderManagement(props));

    await act(async () => {
      await result.current.handleCreateFolder();
    });

    expect(createFolder).not.toHaveBeenCalled();
    expect(props.setSelectedFolderId).not.toHaveBeenCalled();
    expect(props.startNewChat).not.toHaveBeenCalled();
  });

  it("refreshes the selected folder after rename and preserves the metadata refresh", async () => {
    const props = createProps();
    const { result } = renderHook(() => useFolderManagement(props));

    await act(async () => {
      await result.current.handleRenameFolder(5, "Updated", "#123456");
    });

    expect(renameFolder).toHaveBeenCalledWith(5, "Updated", "#123456");
    expect(listFolders).toHaveBeenCalledWith(3);
    expect(props.refreshConversations).toHaveBeenCalledWith(false, 5, 3, 8);
    expect(props.maybeAutoSummarizeConversation).toHaveBeenCalledWith(42, 12);
  });

  it("reorders folders and refreshes the folder list", async () => {
    const props = createProps();
    const { result } = renderHook(() => useFolderManagement(props));

    await act(async () => {
      await result.current.handleMoveFolder(5, "up");
    });

    expect(moveFolder).toHaveBeenCalledWith(5, "up");
    expect(listFolders).toHaveBeenCalledWith(3);
    expect(props.setFolders).toHaveBeenCalledWith([]);
  });

  it("clears the selected folder when deleting it", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const props = createProps({ selectedFolderId: 5 });
    const { result } = renderHook(() => useFolderManagement(props));

    await act(async () => {
      await result.current.handleDeleteFolder(5);
    });

    expect(deleteFolder).toHaveBeenCalledWith(5);
    expect(props.setSelectedFolderId).toHaveBeenCalledWith(null);
    expect(props.startNewChat).toHaveBeenCalledOnce();
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, 3, 8);
  });

  it("switches to a selected folder and clears project selection", async () => {
    const props = createProps();
    const { result } = renderHook(() => useFolderManagement(props));

    await act(async () => {
      await result.current.handleSelectFolder(17);
    });

    expect(props.setSelectedFolderId).toHaveBeenCalledWith(17);
    expect(props.setSelectedProjectId).toHaveBeenCalledWith(null);
    expect(props.startNewChat).toHaveBeenCalledOnce();
    expect(props.refreshConversations).toHaveBeenCalledWith(false, 17, 3, null);
  });

  it("shows an error toast when creating a folder fails", async () => {
    vi.spyOn(window, "prompt").mockReturnValue("Research");
    createFolder.mockRejectedValueOnce(new Error("create failed"));
    const props = createProps();
    const { result } = renderHook(() => useFolderManagement(props));

    await act(async () => {
      await result.current.handleCreateFolder();
    });

    expect(props.setToast).toHaveBeenCalledWith({
      message: "app.folderCreateError",
      type: "error",
    });
  });

  it("shows an error toast when loading folders fails", async () => {
    listFolders.mockRejectedValueOnce(new Error("load failed"));
    const props = createProps();
    const { result } = renderHook(() => useFolderManagement(props));

    await act(async () => {
      await result.current.refreshFolders();
    });

    expect(props.setToast).toHaveBeenCalledWith({
      message: "app.foldersLoadError",
      type: "error",
    });
  });
});
