import { useCallback, useRef, useState } from "react";
import { getCurrentUser } from "../lib/usersApi";
import { getErrorMessage } from "../lib/errors";

export default function useCurrentUser({ setToast, t }) {
  const [currentUser, setCurrentUser] = useState(null);
  const refreshRequestRef = useRef(0);

  const refreshCurrentUser = useCallback(async () => {
    const requestId = ++refreshRequestRef.current;
    try {
      const user = await getCurrentUser();
      if (requestId !== refreshRequestRef.current) return;
      setCurrentUser(user);
    } catch (error) {
      if (requestId !== refreshRequestRef.current) return;
      setToast({
        message: getErrorMessage(error, t("app.currentUserLoadError")),
        type: "error",
      });
    }
  }, [setToast, t]);

  const resetCurrentUser = useCallback(() => {
    // Ignore any account request that began before logout/reset.
    refreshRequestRef.current += 1;
    setCurrentUser(null);
  }, []);

  return {
    currentUser,
    refreshCurrentUser,
    resetCurrentUser,
  };
}
