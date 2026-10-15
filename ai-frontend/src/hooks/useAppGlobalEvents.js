import { useEffect } from "react";

export default function useAppGlobalEvents({
  logout,
  setCommandPaletteOpen,
  setToast,
  t,
}) {
  useEffect(() => {
    // Any API request can raise this event after a 401, not just chat sending.
    const handleUnauthorized = () => {
      void logout();
      setToast({ message: t("app.sessionExpired"), type: "error" });
    };
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, [logout, setToast, t]);

  useEffect(() => {
    const handleCommandShortcut = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandPaletteOpen((current) => !current);
      }
    };
    window.addEventListener("keydown", handleCommandShortcut);
    return () => window.removeEventListener("keydown", handleCommandShortcut);
  }, [setCommandPaletteOpen]);

  useEffect(() => {
    const handleAppToast = (event) => {
      if (event.detail?.message) {
        setToast({
          message: event.detail.message,
          type: event.detail.type || "error",
        });
      }
    };
    window.addEventListener("app:toast", handleAppToast);
    return () => window.removeEventListener("app:toast", handleAppToast);
  }, [setToast]);
}
