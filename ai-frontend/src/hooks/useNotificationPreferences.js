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
 * Preferences return to defaults outside an authenticated session, and the
 * global change event is observed only while a user is active. Settings
 * changes from other UI surfaces remain synchronized within that session.
 */
export default function useNotificationPreferences({ authed, userId }) {
  const [notificationPreferences, setNotificationPreferences] =
    useState(DEFAULT_PREFERENCES);

  useEffect(() => {
    if (!authed || !userId) {
      setNotificationPreferences(DEFAULT_PREFERENCES);
      return;
    }
    setNotificationPreferences(loadNotificationPreferences(userId));
  }, [authed, userId]);

  useEffect(() => {
    if (!authed || !userId) return;

    const handlePreferenceChange = (event) => {
      if (event.detail) {
        setNotificationPreferences((current) => ({
          ...current,
          ...event.detail,
        }));
      } else {
        setNotificationPreferences(loadNotificationPreferences(userId));
      }
    };

    window.addEventListener(NOTIFICATION_PREFERENCE_EVENT, handlePreferenceChange);
    return () =>
      window.removeEventListener(
        NOTIFICATION_PREFERENCE_EVENT,
        handlePreferenceChange
      );
  }, [authed, userId]);

  const setRealtimeToastsEnabled = useCallback(
    (enabled) => {
      if (!authed || !userId) return;

      const next = { realtimeToasts: enabled };
      setNotificationPreferences(next);
      saveNotificationPreferences(userId, next);
    },
    [authed, userId]
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
