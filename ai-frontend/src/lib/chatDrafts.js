const DRAFT_KEY_PREFIX = "ai-chat-draft";

function getDraftKey(userId, conversationId) {
  const owner = String(userId);
  const conversation = conversationId === null || conversationId === undefined
    ? "new"
    : String(conversationId);
  return `${DRAFT_KEY_PREFIX}:${owner}:${conversation}`;
}

export function loadChatDraft(userId, conversationId) {
  if (!userId || typeof window === "undefined") return "";
  try {
    return window.localStorage.getItem(getDraftKey(userId, conversationId)) || "";
  } catch {
    return "";
  }
}

export function saveChatDraft(userId, conversationId, value) {
  if (!userId || typeof window === "undefined") return;
  try {
    const key = getDraftKey(userId, conversationId);
    const normalized = String(value ?? "");
    if (normalized.trim()) {
      window.localStorage.setItem(key, normalized);
    } else {
      window.localStorage.removeItem(key);
    }
  } catch {
    // Local storage can be unavailable or full; drafts are best-effort.
  }
}

export function clearChatDraft(userId, conversationId) {
  if (!userId || typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(getDraftKey(userId, conversationId));
  } catch {
    // Best-effort cleanup.
  }
}
