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

  it("ignores a pending response after logout resets the current user", async () => {
    let resolveRequest;
    getCurrentUser.mockImplementation(
      () => new Promise((resolve) => {
        resolveRequest = resolve;
      })
    );
    const options = { setToast: vi.fn(), t: (key) => key };
    const { result } = renderHook(() => useCurrentUser(options));
    let pendingRequest;

    act(() => {
      pendingRequest = result.current.refreshCurrentUser();
    });
    act(() => {
      result.current.resetCurrentUser();
    });

    await act(async () => {
      resolveRequest({ id: 99, email: "previous-user@example.com" });
      await pendingRequest;
    });

    expect(result.current.currentUser).toBeNull();
    expect(options.setToast).not.toHaveBeenCalled();
  });

  it("keeps the latest user when overlapping refreshes resolve out of order", async () => {
    let resolveOldRequest;
    let resolveLatestRequest;
    getCurrentUser
      .mockImplementationOnce(
        () => new Promise((resolve) => {
          resolveOldRequest = resolve;
        })
      )
      .mockImplementationOnce(
        () => new Promise((resolve) => {
          resolveLatestRequest = resolve;
        })
      );

    const options = { setToast: vi.fn(), t: (key) => key };
    const { result } = renderHook(() => useCurrentUser(options));
    let oldRequest;
    let latestRequest;

    act(() => {
      oldRequest = result.current.refreshCurrentUser();
      latestRequest = result.current.refreshCurrentUser();
    });

    await act(async () => {
      resolveLatestRequest({ id: 2, email: "current@example.com" });
      await latestRequest;
    });
    await act(async () => {
      resolveOldRequest({ id: 1, email: "stale@example.com" });
      await oldRequest;
    });

    expect(result.current.currentUser).toEqual({
      id: 2,
      email: "current@example.com",
    });
    expect(options.setToast).not.toHaveBeenCalled();
  });
});
