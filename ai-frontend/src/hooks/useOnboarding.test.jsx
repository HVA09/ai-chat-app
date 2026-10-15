import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import useOnboarding from "./useOnboarding";

describe("useOnboarding", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("shows onboarding for a signed-in user who has not completed it", async () => {
    const { result } = renderHook(() =>
      useOnboarding({ authed: true, userId: 7 })
    );

    await waitFor(() => {
      expect(result.current.showOnboarding).toBe(true);
    });
  });

  it("keeps onboarding hidden when the user has completed it", async () => {
    window.localStorage.setItem("ai-chat-onboarding:7", "done");

    const { result } = renderHook(() =>
      useOnboarding({ authed: true, userId: 7 })
    );

    await waitFor(() => {
      expect(result.current.showOnboarding).toBe(false);
    });
  });

  it("persists dismissal for the current user", async () => {
    const { result } = renderHook(() =>
      useOnboarding({ authed: true, userId: 7 })
    );

    await waitFor(() => {
      expect(result.current.showOnboarding).toBe(true);
    });

    act(() => {
      result.current.closeOnboarding();
    });

    expect(result.current.showOnboarding).toBe(false);
    expect(window.localStorage.getItem("ai-chat-onboarding:7")).toBe("done");
  });

  it("resets onboarding when auth ends and evaluates the next user's state", async () => {
    window.localStorage.setItem("ai-chat-onboarding:7", "done");
    const { result, rerender } = renderHook(
      ({ authed, userId }) => useOnboarding({ authed, userId }),
      { initialProps: { authed: true, userId: 7 } }
    );

    await waitFor(() => {
      expect(result.current.showOnboarding).toBe(false);
    });

    rerender({ authed: false, userId: 7 });
    await waitFor(() => {
      expect(result.current.showOnboarding).toBe(false);
    });

    rerender({ authed: true, userId: 8 });
    await waitFor(() => {
      expect(result.current.showOnboarding).toBe(true);
    });
  });
});
