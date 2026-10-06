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
    } catch {
      // تجاهل بصمت — مو حرج
    }
  }, []);

  const handleMarkAllNotificationsRead = useCallback(async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      // تجاهل بصمت — مو حرج
    }
  }, []);

  useEffect(() => {
    if (authed) {
      refreshNotifications();
    }
  }, [authed, refreshNotifications]);

  useEffect(() => {
    if (!authed) return;

    const ws = new WebSocket(buildNotificationsWebSocketUrl());
    ws.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      setNotifications((prev) => [notification, ...prev]);
      if (notificationPreferences.realtimeToasts) {
        setToast({ message: notification.title, type: "success" });
      }
    };

    return () => ws.close();
  }, [authed, notificationPreferences.realtimeToasts, setToast]);

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
