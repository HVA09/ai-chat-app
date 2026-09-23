import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  loadNotificationPreferences,
  saveNotificationPreferences,
  NOTIFICATION_PREFERENCE_EVENT,
} from "./notificationPreferences";

describe("notificationPreferences", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("returns realtime toasts enabled by default", () => {
    expect(loadNotificationPreferences(7)).toEqual({ realtimeToasts: true });
  });

  it("persists and emits preference updates", () => {
    const listener = vi.fn();
    window.addEventListener(NOTIFICATION_PREFERENCE_EVENT, listener);

    saveNotificationPreferences(7, { realtimeToasts: false });

    expect(loadNotificationPreferences(7)).toEqual({ realtimeToasts: false });
    expect(listener).toHaveBeenCalledTimes(1);

    window.removeEventListener(NOTIFICATION_PREFERENCE_EVENT, listener);
  });
});
