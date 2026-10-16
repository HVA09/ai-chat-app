import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  listAssistants,
  listWorkspaceSharedAssistants,
  createAssistant,
  updateAssistant,
  deleteAssistant,
  shareAssistantWithWorkspace,
  unshareAssistantFromWorkspace,
} from "../lib/assistantsApi";
import useAssistantManagement from "./useAssistantManagement";

vi.mock("../lib/assistantsApi", () => ({
  listAssistants: vi.fn(),
  listWorkspaceSharedAssistants: vi.fn(),
  createAssistant: vi.fn(),
  updateAssistant: vi.fn(),
  deleteAssistant: vi.fn(),
  shareAssistantWithWorkspace: vi.fn(),
  unshareAssistantFromWorkspace: vi.fn(),
}));

function createProps(overrides = {}) {
  return {
    selectedWorkspaceId: 3,
    assistantRequestGenerationRef: { current: 0 },
    selectedAssistantId: null,
    editingAssistantId: null,
    setAssistants: vi.fn(),
    setSelectedAssistantId: vi.fn(),
    setEditingAssistantId: vi.fn(),
    setShowAssistantEditor: vi.fn(),
    setToast: vi.fn(),
    startNewChat: vi.fn(),
    t: (key) => key,
    ...overrides,
  };
}

describe("useAssistantManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAssistants.mockResolvedValue([{ id: 1, name: "Owned" }]);
    listWorkspaceSharedAssistants.mockResolvedValue([]);
    createAssistant.mockResolvedValue({ id: 9, name: "New assistant" });
    updateAssistant.mockResolvedValue({ id: 7, name: "Updated" });
    deleteAssistant.mockResolvedValue(undefined);
    shareAssistantWithWorkspace.mockResolvedValue(undefined);
    unshareAssistantFromWorkspace.mockResolvedValue(undefined);
  });

  it("merges owned and shared assistants and clears a missing selection", async () => {
    listWorkspaceSharedAssistants.mockResolvedValue([
      { id: 1, workspace_id: 3, owner_email: "owner@example.com" },
      { id: 2, name: "Shared", workspace_id: 3, owner_email: "other@example.com", can_edit: false },
    ]);
    const props = createProps({ selectedAssistantId: 99 });
    const { result } = renderHook(() => useAssistantManagement(props));

    await act(async () => {
      await result.current.refreshAssistants();
    });

    expect(listWorkspaceSharedAssistants).toHaveBeenCalledWith(3);
    expect(props.setAssistants).toHaveBeenCalledWith([
      {
        id: 1,
        name: "Owned",
        is_shared: true,
        shared_workspace_id: 3,
        owner_email: "owner@example.com",
        can_edit: true,
      },
      {
        id: 2,
        name: "Shared",
        workspace_id: 3,
        owner_email: "other@example.com",
        can_edit: false,
      },
    ]);
    expect(props.setSelectedAssistantId).toHaveBeenCalledWith(null);
  });

  it("creates an assistant, selects it, and starts a new chat", async () => {
    listAssistants.mockResolvedValue([{ id: 9, name: "New assistant" }]);
    const props = createProps();
    const { result } = renderHook(() => useAssistantManagement(props));

    await act(async () => {
      await result.current.handleSaveAssistant({
        name: "Tutor",
        description: "English",
        instructions: "Explain simply.",
      });
    });

    expect(createAssistant).toHaveBeenCalledWith({
      name: "Tutor",
      description: "English",
      instructions: "Explain simply.",
    });
    expect(props.setSelectedAssistantId).toHaveBeenCalledWith(9);
    expect(props.setEditingAssistantId).toHaveBeenCalledWith(9);
    expect(props.startNewChat).toHaveBeenCalledTimes(1);
  });

  it("updates an existing assistant without changing a different selection", async () => {
    listAssistants.mockResolvedValue([
      { id: 7, name: "Updated" },
      { id: 8, name: "Other selected" },
    ]);
    const props = createProps({ editingAssistantId: 7, selectedAssistantId: 8 });
    const { result } = renderHook(() => useAssistantManagement(props));

    await act(async () => {
      await result.current.handleSaveAssistant({
        name: "Updated",
        description: null,
        instructions: "New instructions",
      });
    });

    expect(updateAssistant).toHaveBeenCalledWith(7, {
      name: "Updated",
      description: null,
      instructions: "New instructions",
    });
    expect(props.setSelectedAssistantId).not.toHaveBeenCalled();
  });

  it("shares and unshares an assistant with the selected workspace", async () => {
    const props = createProps();
    const { result } = renderHook(() => useAssistantManagement(props));

    await act(async () => {
      await result.current.handleToggleAssistantShare({
        id: 4,
        is_shared: false,
        can_edit: true,
      });
    });
    expect(shareAssistantWithWorkspace).toHaveBeenCalledWith(4, 3);
    expect(props.setToast).toHaveBeenCalledWith({
      message: "app.assistantShared",
      type: "success",
    });

    await act(async () => {
      await result.current.handleToggleAssistantShare({
        id: 4,
        is_shared: true,
        can_edit: true,
      });
    });
    expect(unshareAssistantFromWorkspace).toHaveBeenCalledWith(4, 3);
    expect(props.setToast).toHaveBeenCalledWith({
      message: "app.assistantUnshared",
      type: "success",
    });
  });

  it("reports create errors and rethrows for the editor to preserve its form state", async () => {
    const error = { response: { data: { detail: "Name already exists" } } };
    createAssistant.mockRejectedValueOnce(error);
    const props = createProps();
    const { result } = renderHook(() => useAssistantManagement(props));

    await act(async () => {
      await expect(result.current.handleSaveAssistant({
        name: "Tutor",
        description: null,
        instructions: "Explain simply.",
      })).rejects.toEqual(error);
    });

    expect(props.setToast).toHaveBeenCalledWith({
      message: "Name already exists",
      type: "error",
    });
  });

  it("deletes a selected assistant and resets to a new chat", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const props = createProps({ selectedAssistantId: 1 });
    const { result } = renderHook(() => useAssistantManagement(props));

    await act(async () => {
      await result.current.handleDeleteAssistant(1, "Owned");
    });

    expect(deleteAssistant).toHaveBeenCalledWith(1);
    expect(props.setSelectedAssistantId).toHaveBeenCalledWith(null);
    expect(props.startNewChat).toHaveBeenCalledTimes(1);
    vi.restoreAllMocks();
  });

  it("ignores an older shared-assistant response after a newer workspace refresh", async () => {
    let resolveOldShared;
    let resolveCurrentShared;
    listWorkspaceSharedAssistants
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOldShared = resolve; }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveCurrentShared = resolve; }));
    const props = createProps();
    const { result } = renderHook(() => useAssistantManagement(props));
    let oldRequest;
    let currentRequest;

    act(() => {
      oldRequest = result.current.refreshAssistants(3);
      currentRequest = result.current.refreshAssistants(4);
    });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(listWorkspaceSharedAssistants).toHaveBeenNthCalledWith(1, 3);
    expect(listWorkspaceSharedAssistants).toHaveBeenNthCalledWith(2, 4);
    await act(async () => {
      resolveCurrentShared([{ id: 4, name: "Current shared", workspace_id: 4, can_edit: false }]);
      await currentRequest;
    });
    await act(async () => {
      resolveOldShared([{ id: 3, name: "Stale shared", workspace_id: 3, can_edit: false }]);
      await oldRequest;
    });

    expect(props.setAssistants).toHaveBeenCalledTimes(1);
    expect(props.setAssistants).toHaveBeenCalledWith([
      { id: 1, name: "Owned", is_shared: false, can_edit: true },
      { id: 4, name: "Current shared", workspace_id: 4, can_edit: false },
    ]);
    expect(props.setToast).not.toHaveBeenCalled();
  });

  it("ignores a stale shared-assistant failure after a newer refresh succeeds", async () => {
    let rejectOldShared;
    listWorkspaceSharedAssistants
      .mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectOldShared = reject; }))
      .mockResolvedValueOnce([{ id: 4, name: "Current shared", workspace_id: 4, can_edit: false }]);
    const props = createProps();
    const { result } = renderHook(() => useAssistantManagement(props));
    let oldRequest;
    let currentRequest;

    act(() => {
      oldRequest = result.current.refreshAssistants(3);
      currentRequest = result.current.refreshAssistants(4);
    });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    await act(async () => {
      await currentRequest;
    });
    await act(async () => {
      rejectOldShared(new Error("old workspace failed"));
      await oldRequest;
    });

    expect(props.setAssistants).toHaveBeenCalledTimes(1);
    expect(props.setAssistants).toHaveBeenCalledWith([
      { id: 1, name: "Owned", is_shared: false, can_edit: true },
      { id: 4, name: "Current shared", workspace_id: 4, can_edit: false },
    ]);
    expect(props.setToast).not.toHaveBeenCalled();
  });

  it("ignores a pending assistant refresh after logout invalidates the request generation", async () => {
    let resolvePendingShared;
    listWorkspaceSharedAssistants.mockImplementationOnce(
      () => new Promise((resolve) => { resolvePendingShared = resolve; })
    );
    const props = createProps();
    const { result } = renderHook(() => useAssistantManagement(props));
    let pendingRequest;

    act(() => {
      pendingRequest = result.current.refreshAssistants(3);
    });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    act(() => {
      props.assistantRequestGenerationRef.current += 1;
    });
    await act(async () => {
      resolvePendingShared([{ id: 3, name: "Previous session shared", workspace_id: 3, can_edit: false }]);
      await pendingRequest;
    });

    expect(props.setAssistants).not.toHaveBeenCalled();
    expect(props.setSelectedAssistantId).not.toHaveBeenCalled();
    expect(props.setToast).not.toHaveBeenCalled();
  });
});
