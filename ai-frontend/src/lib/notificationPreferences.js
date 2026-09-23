const PREFIX = "ai-chat-notifications:";

export const NOTIFICATION_PREFERENCE_EVENT = "ai-chat:notification-preferences-changed";

function key(userId) {
  return `${PREFIX}${userId}`;
}

export function loadNotificationPreferences(userId) {
  const defaults = { realtimeToasts: true };
  if (!userId || typeof window === "undefined") return defaults;

  try {
    const raw = window.localStorage.getItem(key(userId));
    if (!raw) return defaults;
    const parsed = JSON.parse(raw);
    return { ...defaults, ...parsed };
  } catch {
    return defaults;
  }
}

export function saveNotificationPreferences(userId, preferences) {
  if (!userId || typeof window === "undefined") return;
  const next = { realtimeToasts: Boolean(preferences.realtimeToasts) };
  try {
    window.localStorage.setItem(key(userId), JSON.stringify(next));
    window.dispatchEvent(
      new CustomEvent(NOTIFICATION_PREFERENCE_EVENT, { detail: next })
    );
  } catch {
    // Preferences are best-effort only.
  }
}
