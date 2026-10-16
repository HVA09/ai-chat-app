import { act, renderHook, waitFor } from "@testing-library/react";
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
    workspaceRequestGenerationRef: { current: 0 },
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

  it("keeps the newest workspace list when requests resolve out of order", async () => {
    const staleList = [{ id: 7, name: "Old workspace" }];
    const currentList = [{ id: 8, name: "Current workspace", default_ai_model: "model-c" }];
    let resolveStale;
    listWorkspaces
      .mockImplementationOnce(
        () => new Promise((resolve) => { resolveStale = resolve; })
      )
      .mockResolvedValueOnce(currentList);
    const props = createProps();
    const { result } = renderHook(() => useWorkspaceManagement(props));
    let staleRequest;
    let currentRequest;

    act(() => {
      staleRequest = result.current.refreshWorkspaces();
      currentRequest = result.current.refreshWorkspaces();
    });

    await act(async () => {
      await currentRequest;
    });
    await act(async () => {
      resolveStale(staleList);
      await staleRequest;
    });

    expect(props.setWorkspaces).toHaveBeenCalledOnce();
    expect(props.setWorkspaces).toHaveBeenCalledWith(currentList);
    expect(props.setSelectedWorkspaceId).toHaveBeenCalledOnce();
    expect(props.setSelectedWorkspaceId).toHaveBeenCalledWith(8);
    expect(props.refreshFolders).toHaveBeenCalledOnce();
    expect(props.refreshFolders).toHaveBeenCalledWith(8);
    expect(props.refreshProjects).toHaveBeenCalledOnce();
    expect(props.refreshProjects).toHaveBeenCalledWith(8);
    expect(props.refreshAssistants).toHaveBeenCalledOnce();
    expect(props.refreshAssistants).toHaveBeenCalledWith(8);
    expect(props.refreshConversations).toHaveBeenCalledOnce();
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, 8, null);
    expect(props.setToast).not.toHaveBeenCalled();
  });

  it("ignores an older workspace-list failure after a newer refresh succeeds", async () => {
    const currentList = [{ id: 8, name: "Current workspace", default_ai_model: "model-c" }];
    let rejectStale;
    listWorkspaces
      .mockImplementationOnce(
        () => new Promise((_resolve, reject) => { rejectStale = reject; })
      )
      .mockResolvedValueOnce(currentList);
    const props = createProps();
    const { result } = renderHook(() => useWorkspaceManagement(props));
    let staleRequest;
    let currentRequest;

    act(() => {
      staleRequest = result.current.refreshWorkspaces();
      currentRequest = result.current.refreshWorkspaces();
    });

    await act(async () => {
      await currentRequest;
    });
    await act(async () => {
      rejectStale(new Error("older workspace request failed"));
      await staleRequest;
    });

    expect(props.setWorkspaces).toHaveBeenCalledOnce();
    expect(props.setWorkspaces).toHaveBeenCalledWith(currentList);
    expect(props.setToast).not.toHaveBeenCalled();
    expect(props.refreshConversations).toHaveBeenCalledOnce();
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, 8, null);
  });

  it("stops an older refresh cascade if a newer workspace refresh starts during folder loading", async () => {
    const oldList = [{ id: 2, name: "Old context", default_ai_model: "model-b" }];
    const currentList = [{ id: 3, name: "Current context", default_ai_model: "model-c" }];
    let resolveOldFolders;
    listWorkspaces
      .mockResolvedValueOnce(oldList)
      .mockResolvedValueOnce(currentList);
    const props = createProps({
      refreshFolders: vi.fn()
        .mockImplementationOnce(() => new Promise((resolve) => { resolveOldFolders = resolve; }))
        .mockResolvedValue(undefined),
    });
    const { result } = renderHook(() => useWorkspaceManagement(props));
    let oldRequest;

    act(() => {
      oldRequest = result.current.refreshWorkspaces();
    });
    await waitFor(() => {
      expect(props.refreshFolders).toHaveBeenCalledWith(2);
    });

    let currentRequest;
    act(() => {
      currentRequest = result.current.refreshWorkspaces();
    });
    await act(async () => {
      await currentRequest;
    });

    await act(async () => {
      resolveOldFolders();
      await oldRequest;
    });

    expect(props.refreshFolders).toHaveBeenCalledTimes(2);
    expect(props.refreshFolders).toHaveBeenNthCalledWith(1, 2);
    expect(props.refreshFolders).toHaveBeenNthCalledWith(2, 3);
    expect(props.refreshProjects).toHaveBeenCalledOnce();
    expect(props.refreshProjects).toHaveBeenCalledWith(3);
    expect(props.refreshAssistants).toHaveBeenCalledOnce();
    expect(props.refreshAssistants).toHaveBeenCalledWith(3);
    expect(props.refreshConversations).toHaveBeenCalledOnce();
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, 3, null);
  });

  it("does not restore workspaces when a pending refresh resolves after logout invalidation", async () => {
    let resolvePending;
    listWorkspaces.mockImplementationOnce(
      () => new Promise((resolve) => { resolvePending = resolve; })
    );
    const generationRef = { current: 0 };
    const props = createProps({ workspaceRequestGenerationRef: generationRef });
    const { result } = renderHook(() => useWorkspaceManagement(props));
    let pendingRequest;

    act(() => {
      pendingRequest = result.current.refreshWorkspaces();
    });
    act(() => {
      generationRef.current += 1;
    });
    await act(async () => {
      resolvePending([{ id: 8, name: "Previous session workspace" }]);
      await pendingRequest;
    });

    expect(props.setWorkspaces).not.toHaveBeenCalled();
    expect(props.setSelectedWorkspaceId).not.toHaveBeenCalled();
    expect(props.setSelectedModel).not.toHaveBeenCalled();
    expect(props.setToast).not.toHaveBeenCalled();
    expect(props.refreshFolders).not.toHaveBeenCalled();
    expect(props.refreshProjects).not.toHaveBeenCalled();
    expect(props.refreshAssistants).not.toHaveBeenCalled();
    expect(props.refreshConversations).not.toHaveBeenCalled();
  });

  it("stops an older workspace selection cascade after a newer selection", async () => {
    let resolveOlderFolders;
    const props = createProps({
      refreshFolders: vi.fn()
        .mockImplementationOnce(() => new Promise((resolve) => { resolveOlderFolders = resolve; }))
        .mockResolvedValue(undefined),
    });
    const { result } = renderHook(() => useWorkspaceManagement(props));
    let olderSelection;

    act(() => {
      olderSelection = result.current.handleSelectWorkspace("3");
    });
    await waitFor(() => {
      expect(props.refreshFolders).toHaveBeenCalledWith(3);
    });

    let newerSelection;
    act(() => {
      newerSelection = result.current.handleSelectWorkspace("4");
    });
    await act(async () => {
      await newerSelection;
    });

    await act(async () => {
      resolveOlderFolders();
      await olderSelection;
    });

    expect(props.refreshFolders).toHaveBeenCalledTimes(2);
    expect(props.refreshProjects).toHaveBeenCalledOnce();
    expect(props.refreshProjects).toHaveBeenCalledWith(4);
    expect(props.refreshAssistants).toHaveBeenCalledOnce();
    expect(props.refreshAssistants).toHaveBeenCalledWith(4);
    expect(props.refreshConversations).toHaveBeenCalledOnce();
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, 4, null);
  });

});
