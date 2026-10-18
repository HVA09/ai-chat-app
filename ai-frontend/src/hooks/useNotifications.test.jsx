import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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

class MockWebSocket {
  static instances = [];

  constructor(url) {
    this.url = url;
    this.close = vi.fn();
    MockWebSocket.instances.push(this);
  }

  emitMessage(data) {
    this.onmessage?.({ data });
  }

  emitError() {
    this.onerror?.(new Event("error"));
  }
}

function setupHook({ authed = false, realtimeToasts = false } = {}) {
  const setToast = vi.fn();
  const hook = renderHook(() =>
    useNotifications({
      authed,
      notificationPreferences: { realtimeToasts },
      setToast,
    })
  );
  return { ...hook, setToast };
}

describe("useNotifications", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockWebSocket.instances = [];
    vi.stubGlobal("WebSocket", MockWebSocket);
    listNotifications.mockResolvedValue([]);
    markNotificationRead.mockResolvedValue({});
    markAllNotificationsRead.mockResolvedValue({});
  });

  afterEach(() => {
    vi.unstubAllGlobals();
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

  it("does not restore notifications when a pending refresh resolves after reset", async () => {
    const stale = [{ id: 8, title: "Stale notification", is_read: false }];
    let resolvePending;
    listNotifications.mockImplementationOnce(
      () => new Promise((resolve) => {
        resolvePending = resolve;
      })
    );
    const { result, setToast } = setupHook();

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.refreshNotifications();
    });
    act(() => {
      result.current.resetNotifications();
    });
    expect(result.current.notifications).toEqual([]);

    await act(async () => {
      resolvePending(stale);
      await pendingRequest;
    });

    expect(result.current.notifications).toEqual([]);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("keeps the newest result when overlapping notification refreshes resolve out of order", async () => {
    const stale = [{ id: 8, title: "Older response", is_read: false }];
    const current = [{ id: 9, title: "Newest response", is_read: false }];
    let resolveOlder;
    let resolveCurrent;
    listNotifications
      .mockImplementationOnce(
        () => new Promise((resolve) => {
          resolveOlder = resolve;
        })
      )
      .mockImplementationOnce(
        () => new Promise((resolve) => {
          resolveCurrent = resolve;
        })
      );
    const { result, setToast } = setupHook();

    let olderRequest;
    let currentRequest;
    act(() => {
      olderRequest = result.current.refreshNotifications();
      currentRequest = result.current.refreshNotifications();
    });

    await act(async () => {
      resolveCurrent(current);
      await currentRequest;
    });
    await act(async () => {
      resolveOlder(stale);
      await olderRequest;
    });

    expect(result.current.notifications).toEqual(current);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("ignores a stale load failure after reset instead of showing an error toast", async () => {
    let rejectPending;
    listNotifications.mockImplementationOnce(
      () => new Promise((_resolve, reject) => {
        rejectPending = reject;
      })
    );
    const { result, setToast } = setupHook();

    let pendingRequest;
    act(() => {
      pendingRequest = result.current.refreshNotifications();
    });
    act(() => {
      result.current.resetNotifications();
    });

    await act(async () => {
      rejectPending(new Error("previous session failed"));
      await pendingRequest;
    });

    expect(result.current.notifications).toEqual([]);
    expect(setToast).not.toHaveBeenCalled();
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
  it("ignores a pending mark-read failure after notifications are reset", async () => {
    const existing = [{ id: 42, title: "Old unread", is_read: false }];
    listNotifications.mockResolvedValueOnce(existing);
    let rejectMarkRead;
    markNotificationRead.mockImplementationOnce(
      () => new Promise((_resolve, reject) => {
        rejectMarkRead = reject;
      })
    );
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.refreshNotifications();
    });

    let pendingAction;
    act(() => {
      pendingAction = result.current.handleMarkNotificationRead(42);
    });
    act(() => {
      result.current.resetNotifications();
    });

    await act(async () => {
      rejectMarkRead(new Error("previous session failed"));
      await pendingAction;
    });

    expect(result.current.notifications).toEqual([]);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("does not let a pending mark-all request modify notifications after reset", async () => {
    const previousSession = [{ id: 42, title: "Previous session", is_read: false }];
    const currentSession = [{ id: 42, title: "Current session", is_read: false }];
    listNotifications.mockResolvedValueOnce(previousSession);
    let resolveMarkAll;
    markAllNotificationsRead.mockImplementationOnce(
      () => new Promise((resolve) => {
        resolveMarkAll = resolve;
      })
    );
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.refreshNotifications();
    });

    let pendingAction;
    act(() => {
      pendingAction = result.current.handleMarkAllNotificationsRead();
    });
    act(() => {
      result.current.resetNotifications();
    });

    listNotifications.mockResolvedValueOnce(currentSession);
    await act(async () => {
      await result.current.refreshNotifications();
    });
    expect(result.current.notifications).toEqual(currentSession);

    await act(async () => {
      resolveMarkAll();
      await pendingAction;
    });

    expect(result.current.notifications).toEqual(currentSession);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("does not apply a pending mark-read success to notifications after reset", async () => {
    const previousSession = [{ id: 42, title: "Previous session", is_read: false }];
    const currentSession = [{ id: 42, title: "Current session", is_read: false }];
    listNotifications.mockResolvedValueOnce(previousSession);
    let resolveMarkRead;
    markNotificationRead.mockImplementationOnce(
      () => new Promise((resolve) => {
        resolveMarkRead = resolve;
      })
    );
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.refreshNotifications();
    });

    let pendingAction;
    act(() => {
      pendingAction = result.current.handleMarkNotificationRead(42);
    });
    act(() => {
      result.current.resetNotifications();
    });

    listNotifications.mockResolvedValueOnce(currentSession);
    await act(async () => {
      await result.current.refreshNotifications();
    });

    await act(async () => {
      resolveMarkRead();
      await pendingAction;
    });

    expect(result.current.notifications).toEqual(currentSession);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("ignores a pending mark-all failure after notifications are reset", async () => {
    const previousSession = [{ id: 42, title: "Previous session", is_read: false }];
    listNotifications.mockResolvedValueOnce(previousSession);
    let rejectMarkAll;
    markAllNotificationsRead.mockImplementationOnce(
      () => new Promise((_resolve, reject) => {
        rejectMarkAll = reject;
      })
    );
    const { result, setToast } = setupHook();

    await act(async () => {
      await result.current.refreshNotifications();
    });

    let pendingAction;
    act(() => {
      pendingAction = result.current.handleMarkAllNotificationsRead();
    });
    act(() => {
      result.current.resetNotifications();
    });

    await act(async () => {
      rejectMarkAll(new Error("previous session failed"));
      await pendingAction;
    });

    expect(result.current.notifications).toEqual([]);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("adds valid realtime notifications and only shows the success toast when enabled", async () => {
    const { result, setToast } = setupHook({ authed: true, realtimeToasts: true });
    const socket = MockWebSocket.instances[0];

    expect(socket.url).toBe("ws://localhost/notifications");
    await act(async () => {
      await result.current.refreshNotifications();
    });
    act(() => {
      socket.emitMessage(JSON.stringify({ id: 9, title: "Live update", is_read: false }));
    });

    expect(result.current.notifications).toEqual([
      { id: 9, title: "Live update", is_read: false },
    ]);
    expect(setToast).toHaveBeenCalledWith({
      message: "Live update",
      type: "success",
    });
  });

  it("ignores queued realtime events from a socket after logout", async () => {
    let authed = true;
    const setToast = vi.fn();
    const { result, rerender } = renderHook(() =>
      useNotifications({
        authed,
        notificationPreferences: { realtimeToasts: true },
        setToast,
      })
    );
    const socket = MockWebSocket.instances[0];

    await act(async () => {
      await result.current.refreshNotifications();
    });

    act(() => {
      authed = false;
      rerender();
    });
    expect(socket.close).toHaveBeenCalledTimes(1);

    act(() => {
      socket.emitMessage(
        JSON.stringify({ id: 99, title: "Late update", is_read: false })
      );
      socket.emitError();
    });

    expect(result.current.notifications).toEqual([]);
    expect(setToast).not.toHaveBeenCalled();
  });

  it("reports malformed or incomplete realtime payloads without throwing", async () => {
    const { result, setToast } = setupHook({ authed: true });
    const socket = MockWebSocket.instances[0];

    await act(async () => {
      await result.current.refreshNotifications();
    });
    act(() => {
      socket.emitMessage("not-json");
      socket.emitMessage(JSON.stringify({ title: "Missing ID" }));
    });

    expect(result.current.notifications).toEqual([]);
    expect(setToast).toHaveBeenCalledTimes(2);
    expect(setToast).toHaveBeenLastCalledWith({
      message: "تعذر استقبال الإشعارات الفورية",
      type: "error",
    });
  });

  it("reports realtime socket errors", () => {
    const { setToast } = setupHook({ authed: true });
    const socket = MockWebSocket.instances[0];

    act(() => {
      socket.emitError();
    });

    expect(setToast).toHaveBeenCalledWith({
      message: "تعذر استقبال الإشعارات الفورية",
      type: "error",
    });
  });

});
