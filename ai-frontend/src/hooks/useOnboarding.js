import { useCallback, useEffect, useState } from "react";

export default function useOnboarding({ authed, userId }) {
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    if (!authed || userId == null || typeof window === "undefined") {
      setShowOnboarding(false);
      return;
    }

    try {
      const key = `ai-chat-onboarding:${userId}`;
      setShowOnboarding(window.localStorage.getItem(key) !== "done");
    } catch {
      // If browser storage is unavailable, keep onboarding available for this session.
      setShowOnboarding(true);
    }
  }, [authed, userId]);

  const closeOnboarding = useCallback(() => {
    if (userId != null && typeof window !== "undefined") {
      try {
        window.localStorage.setItem(`ai-chat-onboarding:${userId}`, "done");
      } catch {
        // Dismiss the modal for this session even if persistence is unavailable.
      }
    }
    setShowOnboarding(false);
  }, [userId]);

  return { showOnboarding, closeOnboarding };
}
