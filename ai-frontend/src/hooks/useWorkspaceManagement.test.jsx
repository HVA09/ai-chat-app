import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createWorkspace,
  listWorkspaces,
  renameWorkspace,
} from "../lib/workspacesApi";
import useWorkspaceManagement from "./useWorkspaceManagement";

vi.mock("../lib/workspacesApi", () => ({
  createWorkspace: vi.fn(),
  listWorkspaces: vi.fn(),
  renameWorkspace: vi.fn(),
}));

vi.mock("../lib/errors", () => ({
  getErrorMessage: vi.fn((_error, fallback) => fallback),
}));

function createProps(overrides = {}) {
  return {
    workspaces: [
      { id: 2, name: "Research", default_ai_model: "model-b", daily_ai_request_limit: 20 },
      { id: 3, name: "Writing", default_ai_model: "model-c", daily_ai_request_limit: null },
    ],
    selectedWorkspaceId: 2,
    aiModels: [
      { id: "model-a", is_default: true },
      { id: "model-b", is_default: false },
    ],
    showArchivedConversations: false,
    setWorkspaces: vi.fn(),
    setSelectedWorkspaceId: vi.fn(),
    setSelectedModel: vi.fn(),
    setSelectedFolderId: vi.fn(),
    setSelectedProjectId: vi.fn(),
    startNewChat: vi.fn(),
    refreshFolders: vi.fn().mockResolvedValue(undefined),
    refreshProjects: vi.fn().mockResolvedValue(undefined),
    refreshAssistants: vi.fn().mockResolvedValue(undefined),
    refreshConversations: vi.fn().mockResolvedValue(undefined),
    setToast: vi.fn(),
    t: (key) => key,
    ...overrides,
  };
}

describe("useWorkspaceManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listWorkspaces.mockResolvedValue([
      { id: 2, name: "Research", default_ai_model: "model-b" },
      { id: 3, name: "Writing", default_ai_model: "model-c" },
    ]);
    createWorkspace.mockResolvedValue({
      id: 9,
      name: "New Team",
      default_ai_model: "model-a",
    });
    renameWorkspace.mockResolvedValue({ id: 2, name: "Renamed" });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("refreshes workspaces while preserving a valid selection and related data", async () => {
    const props = createProps();
    const { result } = renderHook(() => useWorkspaceManagement(props));

    await act(async () => {
      await result.current.refreshWorkspaces();
    });

    expect(listWorkspaces).toHaveBeenCalledOnce();
    expect(props.setWorkspaces).toHaveBeenCalledWith([
      { id: 2, name: "Research", default_ai_model: "model-b" },
      { id: 3, name: "Writing", default_ai_model: "model-c" },
    ]);
    expect(props.setSelectedWorkspaceId).toHaveBeenCalledWith(2);
    expect(props.setSelectedModel).toHaveBeenCalledWith("model-b");
    expect(props.setSelectedFolderId).toHaveBeenCalledWith(null);
    expect(props.setSelectedProjectId).toHaveBeenCalledWith(null);
    expect(props.refreshFolders).toHaveBeenCalledWith(2);
    expect(props.refreshProjects).toHaveBeenCalledWith(2);
    expect(props.refreshAssistants).toHaveBeenCalledWith(2);
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, 2, null);
  });

  it("falls back to the first workspace and default model when the old selection disappeared", async () => {
    listWorkspaces.mockResolvedValueOnce([
      { id: 7, name: "Default workspace" },
    ]);
    const props = createProps({
      selectedWorkspaceId: 99,
      aiModels: [{ id: "model-default", is_default: true }],
    });
    const { result } = renderHook(() => useWorkspaceManagement(props));

    await act(async () => {
      await result.current.refreshWorkspaces();
    });

    expect(props.setSelectedWorkspaceId).toHaveBeenCalledWith(7);
    expect(props.setSelectedModel).toHaveBeenCalledWith("model-default");
    expect(props.refreshFolders).toHaveBeenCalledWith(7);
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, 7, null);
  });

  it("shows an error toast and leaves selection unchanged when workspace loading fails", async () => {
    listWorkspaces.mockRejectedValueOnce(new Error("network failed"));
    const props = createProps();
    const { result } = renderHook(() => useWorkspaceManagement(props));

    await act(async () => {
      await result.current.refreshWorkspaces();
    });

    expect(props.setToast).toHaveBeenCalledWith({
      message: "app.workspacesLoadError",
      type: "error",
    });
    expect(props.setSelectedWorkspaceId).not.toHaveBeenCalled();
    expect(props.refreshConversations).not.toHaveBeenCalled();
  });

  it("creates and selects a workspace, then refreshes its data", async () => {
    vi.spyOn(window, "prompt").mockReturnValue("  New Team  ");
    const props = createProps();
    const { result } = renderHook(() => useWorkspaceManagement(props));

    await act(async () => {
      await result.current.handleCreateWorkspace();
    });

    expect(createWorkspace).toHaveBeenCalledWith("New Team");
    expect(props.setWorkspaces).toHaveBeenCalledWith([
      ...props.workspaces,
      { id: 9, name: "New Team", default_ai_model: "model-a" },
    ]);
    expect(props.setSelectedWorkspaceId).toHaveBeenCalledWith(9);
    expect(props.setSelectedFolderId).toHaveBeenCalledWith(null);
    expect(props.setSelectedProjectId).toHaveBeenCalledWith(null);
    expect(props.startNewChat).toHaveBeenCalledOnce();
    expect(props.refreshFolders).toHaveBeenCalledWith(9);
    expect(props.refreshProjects).toHaveBeenCalledWith(9);
    expect(props.refreshAssistants).toHaveBeenCalledWith(9);
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, 9, null);
  });

  it("does not create a workspace when the prompt is blank", async () => {
    vi.spyOn(window, "prompt").mockReturnValue("   ");
    const props = createProps();
    const { result } = renderHook(() => useWorkspaceManagement(props));

    await act(async () => {
      await result.current.handleCreateWorkspace();
    });

    expect(createWorkspace).not.toHaveBeenCalled();
    expect(props.setSelectedWorkspaceId).not.toHaveBeenCalled();
    expect(props.startNewChat).not.toHaveBeenCalled();
  });

  it("renames the selected workspace without replacing unrelated workspaces", async () => {
    vi.spyOn(window, "prompt").mockReturnValue("  Updated name  ");
    const props = createProps();
    const { result } = renderHook(() => useWorkspaceManagement(props));

    await act(async () => {
      await result.current.handleRenameWorkspace();
    });

    expect(renameWorkspace).toHaveBeenCalledWith(2, "Updated name");
    const updateWorkspaces = props.setWorkspaces.mock.calls[0][0];
    expect(updateWorkspaces(props.workspaces)).toEqual([
      { id: 2, name: "Renamed" },
      props.workspaces[1],
    ]);
  });

  it("switches workspaces and resets folder/project context before loading the new workspace", async () => {
    const props = createProps();
    const { result } = renderHook(() => useWorkspaceManagement(props));

    await act(async () => {
      await result.current.handleSelectWorkspace("3");
    });

    expect(props.setSelectedWorkspaceId).toHaveBeenCalledWith(3);
    expect(props.setSelectedFolderId).toHaveBeenCalledWith(null);
    expect(props.setSelectedProjectId).toHaveBeenCalledWith(null);
    expect(props.setSelectedModel).toHaveBeenCalledWith("model-c");
    expect(props.startNewChat).toHaveBeenCalledOnce();
    expect(props.refreshFolders).toHaveBeenCalledWith(3);
    expect(props.refreshProjects).toHaveBeenCalledWith(3);
    expect(props.refreshAssistants).toHaveBeenCalledWith(3);
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, 3, null);
  });

  it("updates workspace model and quota state with success toasts", () => {
    const props = createProps();
    const { result } = renderHook(() => useWorkspaceManagement(props));
    const modelUpdate = {
      id: 2,
      default_ai_model: "model-new",
      name: "Research renamed",
    };
    const quotaUpdate = { id: 2, daily_ai_request_limit: 50 };

    act(() => {
      result.current.handleWorkspaceUpdated(modelUpdate);
      result.current.handleWorkspaceQuotaUpdated(quotaUpdate);
    });

    const modelUpdater = props.setWorkspaces.mock.calls[0][0];
    const quotaUpdater = props.setWorkspaces.mock.calls[1][0];
    expect(modelUpdater(props.workspaces)[0]).toEqual({
      ...props.workspaces[0],
      ...modelUpdate,
    });
    expect(quotaUpdater(props.workspaces)[0]).toEqual({
      ...props.workspaces[0],
      ...quotaUpdate,
    });
    expect(props.setSelectedModel).toHaveBeenCalledWith("model-new");
    expect(props.setToast).toHaveBeenNthCalledWith(1, {
      message: "app.workspaceModelUpdated",
      type: "success",
    });
    expect(props.setToast).toHaveBeenNthCalledWith(2, {
      message: "app.workspaceQuotaUpdated",
      type: "success",
    });
  });
});
