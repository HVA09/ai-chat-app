import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useNotifications from "./useNotifications";

const {
  listNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  buildNotificationsWebSocketUrl,
} = vi.hoisted(() => ({
  listNotifications: vi.fn(),
  markNotificationRead: vi.fn(),
  markAllNotificationsRead: vi.fn(),
  buildNotificationsWebSocketUrl: vi.fn(() => "ws://localhost/notifications"),
}));

vi.mock("../lib/notificationsApi", () => ({
  listNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  buildNotificationsWebSocketUrl,
}));

function setupHook() {
  const setToast = vi.fn();
  const hook = renderHook(() =>
    useNotifications({
      authed: false,
      notificationPreferences: { realtimeToasts: false },
      setToast,
    })
  );
  return { ...hook, setToast };
}

describe("useNotifications", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listNotifications.mockResolvedValue([]);
    markNotificationRead.mockResolvedValue({});
    markAllNotificationsRead.mockResolvedValue({});
  });

  it("shows a translated fallback and preserves existing notifications when loading fails", async () => {
    const existing = [{ id: 7, title: "Existing", is_read: false }];
    listNotifications.mockResolvedValueOnce(existing);
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.refreshNotifications();
    });
    expect(result.current.notifications).toEqual(existing);

    listNotifications.mockRejectedValueOnce(new Error("offline"));
    await act(async () => {
      await result.current.refreshNotifications();
    });

    expect(setToast).toHaveBeenCalledWith({
      message: "تعذر تحميل الإشعارات",
      type: "error",
    });
    expect(result.current.notifications).toEqual(existing);
  });

  it("shows the API error and preserves notification state when marking one as read fails", async () => {
    const existing = [
      { id: 42, title: "Unread", is_read: false },
      { id: 43, title: "Other", is_read: false },
    ];
    listNotifications.mockResolvedValueOnce(existing);
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.refreshNotifications();
    });

    markNotificationRead.mockRejectedValueOnce({
      response: { data: { detail: "Permission denied" } },
    });
    await act(async () => {
      await result.current.handleMarkNotificationRead(42);
    });

    expect(setToast).toHaveBeenCalledWith({
      message: "Permission denied",
      type: "error",
    });
    expect(result.current.notifications).toEqual(existing);
  });

  it("marks only the requested notification as read after a successful request", async () => {
    const existing = [
      { id: 42, title: "First", is_read: false },
      { id: 43, title: "Second", is_read: false },
    ];
    listNotifications.mockResolvedValueOnce(existing);
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.refreshNotifications();
      await result.current.handleMarkNotificationRead(42);
    });

    expect(result.current.notifications).toEqual([
      { ...existing[0], is_read: true },
      existing[1],
    ]);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("shows a translated fallback and preserves state when marking all as read fails", async () => {
    const existing = [
      { id: 42, title: "First", is_read: false },
      { id: 43, title: "Second", is_read: false },
    ];
    listNotifications.mockResolvedValueOnce(existing);
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.refreshNotifications();
    });

    markAllNotificationsRead.mockRejectedValueOnce(new Error("offline"));
    await act(async () => {
      await result.current.handleMarkAllNotificationsRead();
    });

    expect(setToast).toHaveBeenCalledWith({
      message: "تعذر تحديث حالة الإشعارات",
      type: "error",
    });
    expect(result.current.notifications).toEqual(existing);
  });

  it("marks all notifications as read only after a successful request", async () => {
    const existing = [
      { id: 42, title: "First", is_read: false },
      { id: 43, title: "Second", is_read: true },
    ];
    listNotifications.mockResolvedValueOnce(existing);
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.refreshNotifications();
      await result.current.handleMarkAllNotificationsRead();
    });

    expect(result.current.notifications).toEqual(
      existing.map((notification) => ({ ...notification, is_read: true }))
    );
    expect(setToast).not.toHaveBeenCalled();
  });
});
