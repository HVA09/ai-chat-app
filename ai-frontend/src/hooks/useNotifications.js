import { useCallback, useEffect, useState } from "react";
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

  const refreshNotifications = useCallback(async () => {
    try {
      setNotifications(await listNotifications());
    } catch (err) {
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

    const ws = new WebSocket(buildNotificationsWebSocketUrl());
    ws.onmessage = (event) => {
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
    ws.onerror = showRealtimeError;

    return () => ws.close();
  }, [
    authed,
    notificationPreferences.realtimeToasts,
    setToast,
    showRealtimeError,
  ]);

  const resetNotifications = useCallback(() => {
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
