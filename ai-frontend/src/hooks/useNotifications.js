import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  buildNotificationsWebSocketUrl,
} from "../lib/notificationsApi";
import {
  loadNotificationPreferences,
  saveNotificationPreferences,
  NOTIFICATION_PREFERENCE_EVENT,
} from "../lib/notificationPreferences";
import { getErrorMessage } from "../lib/errors";

export default function useNotifications({ setToast, authed, currentUserId }) {
  const { t } = useTranslation();
  const [notifications, setNotifications] = useState([]);
  const [notificationPreferences, setNotificationPreferences] = useState({
    realtimeToasts: true,
  });

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

  const resetNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  useEffect(() => {
    if (!authed || !currentUserId) return;
    setNotificationPreferences(loadNotificationPreferences(currentUserId));
  }, [authed, currentUserId]);

  useEffect(() => {
    const handlePreferenceChange = (event) => {
      if (event.detail) {
        setNotificationPreferences((current) => ({ ...current, ...event.detail }));
      } else if (currentUserId) {
        setNotificationPreferences(loadNotificationPreferences(currentUserId));
      }
    };

    window.addEventListener(NOTIFICATION_PREFERENCE_EVENT, handlePreferenceChange);
    return () => window.removeEventListener(NOTIFICATION_PREFERENCE_EVENT, handlePreferenceChange);
  }, [currentUserId]);

  useEffect(() => {
    if (!authed || !currentUserId || typeof window === "undefined") return undefined;

    const ws = new WebSocket(buildNotificationsWebSocketUrl());
    ws.onmessage = (event) => {
      try {
        const notification = JSON.parse(event.data);
        setNotifications((prev) => [notification, ...prev]);
        if (notificationPreferences.realtimeToasts) {
          setToast({ message: notification.title, type: "success" });
        }
      } catch {
        // Ignore malformed realtime notification payloads.
      }
    };

    return () => ws.close();
  }, [authed, currentUserId, notificationPreferences.realtimeToasts, setToast]);

  const handleNotificationToastsChanged = useCallback(
    (enabled) => {
      if (!currentUserId) return;
      const next = { realtimeToasts: enabled };
      setNotificationPreferences(next);
      saveNotificationPreferences(currentUserId, next);
    },
    [currentUserId]
  );

  const handleMarkNotificationRead = useCallback(async (id) => {
    try {
      await markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((notification) =>
          notification.id === id ? { ...notification, is_read: true } : notification
        )
      );
    } catch {
      // Non-critical action; keep current notification state.
    }
  }, []);

  const handleMarkAllNotificationsRead = useCallback(async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) =>
        prev.map((notification) => ({ ...notification, is_read: true }))
      );
    } catch {
      // Non-critical action; keep current notification state.
    }
  }, []);

  return {
    notifications,
    notificationPreferences,
    refreshNotifications,
    resetNotifications,
    handleNotificationToastsChanged,
    handleMarkNotificationRead,
    handleMarkAllNotificationsRead,
  };
}
