import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { listProjectMembers } from "../lib/projectMembersApi";
import useProjectMemberRoles from "./useProjectMemberRoles";

vi.mock("../lib/projectMembersApi", () => ({
  listProjectMembers: vi.fn(),
}));

function createOptions(overrides = {}) {
  return {
    projects: [{ id: 5, owner_id: 99 }],
    selectedProjectId: 5,
    selectedWorkspaceId: 3,
    currentUserId: 12,
    workspaces: [{ id: 3, role: "member" }],
    ...overrides,
  };
}

describe("useProjectMemberRoles", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listProjectMembers.mockResolvedValue([{ user_id: 12, role: "editor" }]);
  });

  it("grants manager role to the project owner without an API request", () => {
    const { result } = renderHook(() =>
      useProjectMemberRoles(createOptions({
        projects: [{ id: 5, owner_id: 12 }],
      }))
    );

    expect(result.current[5]).toBe("manager");
    expect(listProjectMembers).not.toHaveBeenCalled();
  });

  it.each(["owner", "admin"])(
    "grants manager role to a workspace %s without an API request",
    (role) => {
      const { result } = renderHook(() =>
        useProjectMemberRoles(createOptions({
          workspaces: [{ id: 3, role }],
        }))
      );

      expect(result.current[5]).toBe("manager");
      expect(listProjectMembers).not.toHaveBeenCalled();
    }
  );

  it("loads the current user's project membership role", async () => {
    const { result } = renderHook(() =>
      useProjectMemberRoles(createOptions())
    );

    await waitFor(() => expect(result.current[5]).toBe("editor"));
    expect(listProjectMembers).toHaveBeenCalledWith(5);
  });

  it("records a null role when the user is not a project member", async () => {
    listProjectMembers.mockResolvedValueOnce([
      { user_id: 88, role: "viewer" },
    ]);
    const { result } = renderHook(() =>
      useProjectMemberRoles(createOptions())
    );

    await waitFor(() => expect(result.current[5]).toBeNull());
  });

  it("fails closed when project membership cannot be loaded", async () => {
    listProjectMembers.mockRejectedValueOnce(new Error("network unavailable"));
    const { result } = renderHook(() =>
      useProjectMemberRoles(createOptions())
    );

    await waitFor(() => {
      expect(result.current).toHaveProperty("5", null);
    });
  });

  it("ignores a membership response after the selected project changes", async () => {
    let resolveFirstRequest;
    listProjectMembers.mockImplementation((projectId) => {
      if (projectId === 5) {
        return new Promise((resolve) => {
          resolveFirstRequest = resolve;
        });
      }
      return Promise.resolve([{ user_id: 12, role: "viewer" }]);
    });

    const { result, rerender } = renderHook(
      ({ options }) => useProjectMemberRoles(options),
      { initialProps: { options: createOptions() } }
    );

    await waitFor(() => expect(resolveFirstRequest).toBeTypeOf("function"));
    rerender({
      options: createOptions({
        selectedProjectId: 8,
        projects: [
          { id: 5, owner_id: 99 },
          { id: 8, owner_id: 99 },
        ],
      }),
    });

    await waitFor(() => expect(result.current[8]).toBe("viewer"));
    await act(async () => {
      resolveFirstRequest([{ user_id: 12, role: "editor" }]);
    });

    expect(result.current[5]).toBeUndefined();
    expect(result.current[8]).toBe("viewer");
  });
});
