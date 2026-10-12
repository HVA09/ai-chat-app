import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createProject,
  deleteProject,
  listProjects,
  moveConversationToProject,
  updateProject,
} from "../lib/projectsApi";
import useProjectManagement from "./useProjectManagement";

vi.mock("../lib/projectsApi", () => ({
  createProject: vi.fn(),
  deleteProject: vi.fn(),
  listProjects: vi.fn(),
  moveConversationToProject: vi.fn(),
  updateProject: vi.fn(),
}));

vi.mock("../lib/errors", () => ({
  getErrorMessage: vi.fn((_error, fallback) => fallback),
}));

function createProps(overrides = {}) {
  return {
    projects: [{ id: 5, name: "Existing", assistant_id: 12 }],
    selectedWorkspaceId: 3,
    selectedProjectId: 5,
    selectedFolderId: 6,
    editingProjectId: null,
    showArchivedConversations: false,
    conversationId: 42,
    setProjects: vi.fn(),
    setSelectedProjectId: vi.fn(),
    setSelectedFolderId: vi.fn(),
    setSelectedAssistantId: vi.fn(),
    setShowProjectEditor: vi.fn(),
    setEditingProjectId: vi.fn(),
    startNewChat: vi.fn(),
    refreshConversations: vi.fn().mockResolvedValue(undefined),
    setToast: vi.fn(),
    t: (key, values) => (values ? `${key}:${values.name}` : key),
    ...overrides,
  };
}

describe("useProjectManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listProjects.mockResolvedValue([{ id: 5, name: "Existing", assistant_id: 12 }]);
    createProject.mockResolvedValue({ id: 19, name: "Research" });
    updateProject.mockResolvedValue({ id: 5, name: "Updated" });
    deleteProject.mockResolvedValue({});
    moveConversationToProject.mockResolvedValue({ project_id: 2 });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loads projects and preserves the current selection only when it still exists", async () => {
    const loaded = [{ id: 5, name: "Existing" }, { id: 8, name: "Other" }];
    listProjects.mockResolvedValueOnce(loaded);
    const props = createProps();
    const { result } = renderHook(() => useProjectManagement(props));

    await act(async () => {
      await result.current.refreshProjects();
    });

    expect(listProjects).toHaveBeenCalledWith(3);
    expect(props.setProjects).toHaveBeenCalledWith(loaded);
    const selectExisting = props.setSelectedProjectId.mock.calls[0][0];
    expect(selectExisting(5)).toBe(5);
    expect(selectExisting(99)).toBeNull();
  });

  it("clears projects when there is no selected workspace", async () => {
    const props = createProps({ selectedWorkspaceId: null });
    const { result } = renderHook(() => useProjectManagement(props));

    await act(async () => {
      await result.current.refreshProjects();
    });

    expect(listProjects).not.toHaveBeenCalled();
    expect(props.setProjects).toHaveBeenCalledWith([]);
    expect(props.setSelectedProjectId).toHaveBeenCalledWith(null);
  });

  it("creates a project, selects it, and refreshes the project conversation list", async () => {
    const props = createProps({ selectedFolderId: 6 });
    const { result } = renderHook(() => useProjectManagement(props));

    await act(async () => {
      await result.current.handleSaveProject({
        name: "Research",
        description: "",
        instructions: "Use project context",
        assistant_id: undefined,
      });
    });

    expect(createProject).toHaveBeenCalledWith(
      3,
      "Research",
      "",
      "Use project context",
      null
    );
    expect(props.setSelectedProjectId).toHaveBeenLastCalledWith(19);
    expect(props.setSelectedFolderId).toHaveBeenCalledWith(null);
    expect(props.startNewChat).toHaveBeenCalledOnce();
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, 3, 19);
    expect(props.setShowProjectEditor).toHaveBeenCalledWith(false);
    expect(props.setEditingProjectId).toHaveBeenCalledWith(null);
  });

  it("updates a project and refreshes the current project list", async () => {
    const props = createProps({
      editingProjectId: 5,
      selectedProjectId: 5,
      selectedFolderId: 6,
    });
    const { result } = renderHook(() => useProjectManagement(props));

    await act(async () => {
      await result.current.handleSaveProject({
        name: "Updated",
        description: "Details",
        instructions: "",
        assistant_id: 12,
      });
    });

    expect(updateProject).toHaveBeenCalledWith(5, "Updated", "Details", "", 12);
    expect(listProjects).toHaveBeenCalledWith(3);
    expect(props.setSelectedProjectId).toHaveBeenLastCalledWith(5);
    expect(props.refreshConversations).toHaveBeenCalledWith(false, 6, 3, 5);
    expect(props.setShowProjectEditor).toHaveBeenCalledWith(false);
    expect(props.setEditingProjectId).toHaveBeenCalledWith(null);
    expect(props.startNewChat).not.toHaveBeenCalled();
  });

  it("reports a save failure and rethrows it to the editor", async () => {
    const failure = new Error("create failed");
    createProject.mockRejectedValueOnce(failure);
    const props = createProps();
    const { result } = renderHook(() => useProjectManagement(props));

    await act(async () => {
      await expect(result.current.handleSaveProject({
        name: "Research",
        description: "",
        instructions: "",
        assistant_id: null,
      })).rejects.toBe(failure);
    });

    expect(props.setToast).toHaveBeenCalledWith({
      message: "app.projectCreateError",
      type: "error",
    });
    expect(props.setShowProjectEditor).not.toHaveBeenCalled();
  });

  it("does not delete a project when confirmation is cancelled", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const props = createProps();
    const { result } = renderHook(() => useProjectManagement(props));

    await act(async () => {
      await result.current.handleDeleteProject(5, "Existing");
    });

    expect(deleteProject).not.toHaveBeenCalled();
    expect(props.refreshConversations).not.toHaveBeenCalled();
  });

  it("deletes the selected project, starts a new chat, and clears its selection", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const props = createProps({ selectedProjectId: 5 });
    const { result } = renderHook(() => useProjectManagement(props));

    await act(async () => {
      await result.current.handleDeleteProject(5, "Existing");
    });

    expect(deleteProject).toHaveBeenCalledWith(5);
    expect(props.setSelectedProjectId).toHaveBeenCalledWith(null);
    expect(props.startNewChat).toHaveBeenCalledOnce();
    expect(props.refreshConversations).toHaveBeenCalledWith(false, 6, 3, null);
  });

  it("selects a project, sets its assistant, and refreshes conversations", async () => {
    const props = createProps();
    const { result } = renderHook(() => useProjectManagement(props));

    await act(async () => {
      await result.current.handleSelectProject(5);
    });

    expect(props.setSelectedProjectId).toHaveBeenCalledWith(5);
    expect(props.setSelectedFolderId).toHaveBeenCalledWith(null);
    expect(props.setSelectedAssistantId).toHaveBeenCalledWith(12);
    expect(props.startNewChat).toHaveBeenCalledOnce();
    expect(props.refreshConversations).toHaveBeenCalledWith(false, null, 3, 5);
  });

  it("moves the active conversation out of the selected project", async () => {
    const props = createProps({ selectedProjectId: 5, conversationId: 42 });
    const { result } = renderHook(() => useProjectManagement(props));

    await act(async () => {
      await result.current.handleMoveConversationToProject(42, "");
    });

    expect(moveConversationToProject).toHaveBeenCalledWith(42, null);
    expect(props.startNewChat).toHaveBeenCalledOnce();
    expect(props.refreshConversations).toHaveBeenCalledWith(false, 6, 3, 5);
  });

  it("reports a move failure through the global toast", async () => {
    moveConversationToProject.mockRejectedValueOnce({
      response: { data: { detail: "move failed" } },
    });
    const props = createProps();
    const { result } = renderHook(() => useProjectManagement(props));

    await act(async () => {
      await result.current.handleMoveConversationToProject(42, 8);
    });

    expect(props.setToast).toHaveBeenCalledWith({
      message: "move failed",
      type: "error",
    });
  });
});
