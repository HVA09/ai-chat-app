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

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key) => key }),
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

describe("useNotifications error feedback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listNotifications.mockResolvedValue([]);
    markNotificationRead.mockResolvedValue({});
    markAllNotificationsRead.mockResolvedValue({});
  });

  it("shows a global toast when marking one notification as read fails", async () => {
    markNotificationRead.mockRejectedValueOnce({
      response: { data: { detail: "Permission denied" } },
    });
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.handleMarkNotificationRead(42);
    });

    expect(setToast).toHaveBeenCalledWith({
      message: "Permission denied",
      type: "error",
    });
  });

  it("shows a translated fallback when marking all notifications as read fails", async () => {
    markAllNotificationsRead.mockRejectedValueOnce(new Error("offline"));
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.handleMarkAllNotificationsRead();
    });

    expect(setToast).toHaveBeenCalledWith({
      message: "app.notificationsReadAllError",
      type: "error",
    });
  });
});
