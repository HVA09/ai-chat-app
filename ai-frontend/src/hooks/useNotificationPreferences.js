import { useCallback, useEffect, useState } from "react";
import {
  loadNotificationPreferences,
  saveNotificationPreferences,
  NOTIFICATION_PREFERENCE_EVENT,
} from "../lib/notificationPreferences";

const DEFAULT_PREFERENCES = {
  realtimeToasts: true,
};

/**
 * Owns persisted notification preferences for the authenticated user.
 *
 * The hook subscribes to the existing global preference event so settings
 * changes from other UI surfaces remain synchronized.
 */
export default function useNotificationPreferences({ authed, userId }) {
  const [notificationPreferences, setNotificationPreferences] =
    useState(DEFAULT_PREFERENCES);

  useEffect(() => {
    if (!authed || !userId) return;
    setNotificationPreferences(loadNotificationPreferences(userId));
  }, [authed, userId]);

  useEffect(() => {
    const handlePreferenceChange = (event) => {
      if (event.detail) {
        setNotificationPreferences((current) => ({
          ...current,
          ...event.detail,
        }));
      } else if (userId) {
        setNotificationPreferences(loadNotificationPreferences(userId));
      }
    };

    window.addEventListener(NOTIFICATION_PREFERENCE_EVENT, handlePreferenceChange);
    return () =>
      window.removeEventListener(
        NOTIFICATION_PREFERENCE_EVENT,
        handlePreferenceChange
      );
  }, [userId]);

  const setRealtimeToastsEnabled = useCallback(
    (enabled) => {
      if (!userId) return;

      const next = { realtimeToasts: enabled };
      setNotificationPreferences(next);
      saveNotificationPreferences(userId, next);
    },
    [userId]
  );

  const resetNotificationPreferences = useCallback(() => {
    setNotificationPreferences(DEFAULT_PREFERENCES);
  }, []);

  return {
    notificationPreferences,
    setRealtimeToastsEnabled,
    resetNotificationPreferences,
  };
}
