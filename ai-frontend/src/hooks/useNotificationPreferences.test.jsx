import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import {
  NOTIFICATION_PREFERENCE_EVENT,
} from "../lib/notificationPreferences";
import useNotificationPreferences from "./useNotificationPreferences";

const defaults = { realtimeToasts: true };

function renderPreferences(initialProps = { authed: true, userId: 1 }) {
  return renderHook(
    ({ authed, userId }) => useNotificationPreferences({ authed, userId }),
    { initialProps }
  );
}

function storePreferences(userId, preferences) {
  window.localStorage.setItem(
    `ai-chat-notifications:${userId}`,
    JSON.stringify(preferences)
  );
}

describe("useNotificationPreferences", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("loads preferences for the authenticated user", () => {
    storePreferences(17, { realtimeToasts: false });

    const { result } = renderPreferences({ authed: true, userId: 17 });

    expect(result.current.notificationPreferences).toEqual({
      realtimeToasts: false,
    });
  });

  it("loads the correct preferences when the active user changes", () => {
    storePreferences(17, { realtimeToasts: false });
    storePreferences(18, { realtimeToasts: true });

    const { result, rerender } = renderPreferences({
      authed: true,
      userId: 17,
    });
    expect(result.current.notificationPreferences).toEqual({
      realtimeToasts: false,
    });

    rerender({ authed: true, userId: 18 });

    expect(result.current.notificationPreferences).toEqual(defaults);
  });

  it("resets to defaults and stops listening to preference events after logout", () => {
    storePreferences(17, { realtimeToasts: false });
    const { result, rerender } = renderPreferences({
      authed: true,
      userId: 17,
    });
    expect(result.current.notificationPreferences).toEqual({
      realtimeToasts: false,
    });

    rerender({ authed: false, userId: null });
    expect(result.current.notificationPreferences).toEqual(defaults);

    act(() => {
      window.dispatchEvent(
        new CustomEvent(NOTIFICATION_PREFERENCE_EVENT, {
          detail: { realtimeToasts: false },
        })
      );
    });

    expect(result.current.notificationPreferences).toEqual(defaults);
  });

  it("persists a preference change for the authenticated user", () => {
    const { result } = renderPreferences({ authed: true, userId: 17 });

    act(() => {
      result.current.setRealtimeToastsEnabled(false);
    });

    expect(result.current.notificationPreferences).toEqual({
      realtimeToasts: false,
    });
    expect(
      JSON.parse(window.localStorage.getItem("ai-chat-notifications:17"))
    ).toEqual({ realtimeToasts: false });
  });

  it("does not persist changes without an authenticated session", () => {
    const { result } = renderPreferences({ authed: false, userId: 17 });

    act(() => {
      result.current.setRealtimeToastsEnabled(false);
    });

    expect(result.current.notificationPreferences).toEqual(defaults);
    expect(window.localStorage.getItem("ai-chat-notifications:17")).toBeNull();
  });

  it("reloads the active user's stored preferences for a change event without detail", () => {
    storePreferences(17, { realtimeToasts: true });
    const { result } = renderPreferences({ authed: true, userId: 17 });

    act(() => {
      storePreferences(17, { realtimeToasts: false });
      window.dispatchEvent(new Event(NOTIFICATION_PREFERENCE_EVENT));
    });

    expect(result.current.notificationPreferences).toEqual({
      realtimeToasts: false,
    });
  });
});
