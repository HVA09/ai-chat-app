import { useCallback, useEffect, useState } from "react";

const AUTO_TITLE_STORAGE_KEY = "ai-chat-auto-title";
const AUTO_SUMMARY_STORAGE_KEY = "ai-chat-auto-summary";

const AUTO_TITLE_EVENT = "ai-chat:auto-title-changed";
const AUTO_SUMMARY_EVENT = "ai-chat:auto-summary-changed";

/**
 * Owns local conversation-generation preferences.
 *
 * The existing storage keys and browser events are preserved so settings UI
 * and App stay synchronized without changing user-facing behavior.
 */
export default function useConversationPreferences() {
  const [autoGenerateTitles, setAutoGenerateTitles] = useState(false);
  const [autoGenerateSummaries, setAutoGenerateSummaries] = useState(false);

  useEffect(() => {
    const readPreference = () => {
      setAutoGenerateTitles(
        window.localStorage.getItem(AUTO_TITLE_STORAGE_KEY) === "true"
      );
    };

    readPreference();
    window.addEventListener(AUTO_TITLE_EVENT, readPreference);
    return () => window.removeEventListener(AUTO_TITLE_EVENT, readPreference);
  }, []);

  useEffect(() => {
    const readPreference = () => {
      setAutoGenerateSummaries(
        window.localStorage.getItem(AUTO_SUMMARY_STORAGE_KEY) === "true"
      );
    };

    readPreference();
    window.addEventListener(AUTO_SUMMARY_EVENT, readPreference);
    return () => window.removeEventListener(AUTO_SUMMARY_EVENT, readPreference);
  }, []);

  const setAutoGenerateTitlesEnabled = useCallback((enabled) => {
    window.localStorage.setItem(AUTO_TITLE_STORAGE_KEY, String(Boolean(enabled)));
    window.dispatchEvent(new Event(AUTO_TITLE_EVENT));
  }, []);

  const setAutoGenerateSummariesEnabled = useCallback((enabled) => {
    window.localStorage.setItem(
      AUTO_SUMMARY_STORAGE_KEY,
      String(Boolean(enabled))
    );
    window.dispatchEvent(new Event(AUTO_SUMMARY_EVENT));
  }, []);

  const resetConversationPreferences = useCallback(() => {
    setAutoGenerateTitles(false);
    setAutoGenerateSummaries(false);
  }, []);

  return {
    autoGenerateTitles,
    autoGenerateSummaries,
    setAutoGenerateTitlesEnabled,
    setAutoGenerateSummariesEnabled,
    resetConversationPreferences,
  };
}
