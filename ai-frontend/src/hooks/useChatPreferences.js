import { useEffect, useState } from "react";

export default function useChatPreferences() {
  const [autoGenerateTitles, setAutoGenerateTitles] = useState(false);
  const [autoGenerateSummaries, setAutoGenerateSummaries] = useState(false);

  useEffect(() => {
    const readPreference = () => {
      setAutoGenerateTitles(
        window.localStorage.getItem("ai-chat-auto-title") === "true"
      );
    };
    readPreference();
    window.addEventListener("ai-chat:auto-title-changed", readPreference);
    return () => window.removeEventListener("ai-chat:auto-title-changed", readPreference);
  }, []);

  useEffect(() => {
    const readPreference = () => {
      setAutoGenerateSummaries(
        window.localStorage.getItem("ai-chat-auto-summary") === "true"
      );
    };
    readPreference();
    window.addEventListener("ai-chat:auto-summary-changed", readPreference);
    return () =>
      window.removeEventListener("ai-chat:auto-summary-changed", readPreference);
  }, []);

  return {
    autoGenerateTitles,
    autoGenerateSummaries,
  };
}
