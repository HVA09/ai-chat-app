import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  listNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  buildNotificationsWebSocketUrl,
} from "../lib/notificationsApi";
import { getErrorMessage } from "../lib/errors";

export default function useNotifications({
  authed,
  notificationPreferences,
  setToast,
}) {
  const { t } = useTranslation();
  const [notifications, setNotifications] = useState([]);
  const refreshRequestRef = useRef(0);

  const refreshNotifications = useCallback(async () => {
    const requestId = ++refreshRequestRef.current;
    try {
      const nextNotifications = await listNotifications();
      if (requestId !== refreshRequestRef.current) return;
      setNotifications(nextNotifications);
    } catch (err) {
      // A stale failure must not show an error for a newer refresh or session.
      if (requestId !== refreshRequestRef.current) return;
      setToast({
        message: getErrorMessage(err, t("app.notificationsLoadError")),
        type: "error",
      });
    }
  }, [setToast, t]);

  const handleMarkNotificationRead = useCallback(async (id) => {
    try {
      await markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch (err) {
      setToast({
        message: getErrorMessage(err, t("app.notificationReadError")),
        type: "error",
      });
    }
  }, [setToast, t]);

  const handleMarkAllNotificationsRead = useCallback(async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (err) {
      setToast({
        message: getErrorMessage(err, t("app.notificationsReadAllError")),
        type: "error",
      });
    }
  }, [setToast, t]);

  useEffect(() => {
    if (authed) {
      refreshNotifications();
    }
  }, [authed, refreshNotifications]);

  const showRealtimeError = useCallback(() => {
    setToast({
      message: t("app.notificationRealtimeError"),
      type: "error",
    });
  }, [setToast, t]);

  useEffect(() => {
    if (!authed) return;

    let active = true;
    const ws = new WebSocket(buildNotificationsWebSocketUrl());
    ws.onmessage = (event) => {
      if (!active) return;
      let notification;
      try {
        notification = JSON.parse(event.data);
      } catch {
        showRealtimeError();
        return;
      }

      if (
        !notification ||
        typeof notification !== "object" ||
        Array.isArray(notification) ||
        (typeof notification.id !== "number" &&
          typeof notification.id !== "string") ||
        typeof notification.title !== "string" ||
        !notification.title.trim()
      ) {
        showRealtimeError();
        return;
      }

      setNotifications((prev) => [notification, ...prev]);
      if (notificationPreferences.realtimeToasts) {
        setToast({ message: notification.title, type: "success" });
      }
    };
    ws.onerror = () => {
      if (active) showRealtimeError();
    };

    return () => {
      // Ignore queued socket events after logout or when replacing this socket.
      active = false;
      ws.close();
    };
  }, [
    authed,
    notificationPreferences.realtimeToasts,
    setToast,
    showRealtimeError,
  ]);

  const resetNotifications = useCallback(() => {
    // Invalidate in-flight loads before clearing user-scoped notification state.
    refreshRequestRef.current += 1;
    setNotifications([]);
  }, []);

  return {
    notifications,
    resetNotifications,
    refreshNotifications,
    handleMarkNotificationRead,
    handleMarkAllNotificationsRead,
  };
}
