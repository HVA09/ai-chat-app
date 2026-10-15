import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getCurrentUser } from "../lib/usersApi";
import useCurrentUser from "./useCurrentUser";

vi.mock("../lib/usersApi", () => ({
  getCurrentUser: vi.fn(),
}));

describe("useCurrentUser", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads and stores the current user", async () => {
    const user = { id: 12, email: "user@example.com" };
    const options = { setToast: vi.fn(), t: (key) => key };
    getCurrentUser.mockResolvedValue(user);

    const { result } = renderHook(() => useCurrentUser(options));

    await act(async () => {
      await result.current.refreshCurrentUser();
    });

    expect(result.current.currentUser).toEqual(user);
    expect(options.setToast).not.toHaveBeenCalled();
  });

  it("shows a useful toast when loading the current user fails", async () => {
    const options = { setToast: vi.fn(), t: (key) => key };
    getCurrentUser.mockRejectedValue({
      response: { data: { detail: "Account service unavailable" } },
    });

    const { result } = renderHook(() => useCurrentUser(options));

    await act(async () => {
      await result.current.refreshCurrentUser();
    });

    expect(result.current.currentUser).toBeNull();
    expect(options.setToast).toHaveBeenCalledWith({
      message: "Account service unavailable",
      type: "error",
    });
  });

  it("resets the current user on logout", async () => {
    const user = { id: 12, email: "user@example.com" };
    const options = { setToast: vi.fn(), t: (key) => key };
    getCurrentUser.mockResolvedValue(user);

    const { result } = renderHook(() => useCurrentUser(options));

    await act(async () => {
      await result.current.refreshCurrentUser();
    });
    expect(result.current.currentUser).toEqual(user);

    act(() => {
      result.current.resetCurrentUser();
    });
    expect(result.current.currentUser).toBeNull();
  });
});
