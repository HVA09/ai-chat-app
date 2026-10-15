import { useCallback, useState } from "react";
import { getCurrentUser } from "../lib/usersApi";
import { getErrorMessage } from "../lib/errors";

export default function useCurrentUser({ setToast, t }) {
  const [currentUser, setCurrentUser] = useState(null);

  const refreshCurrentUser = useCallback(async () => {
    try {
      setCurrentUser(await getCurrentUser());
    } catch (error) {
      setToast({
        message: getErrorMessage(error, t("app.currentUserLoadError")),
        type: "error",
      });
    }
  }, [setToast, t]);

  const resetCurrentUser = useCallback(() => {
    setCurrentUser(null);
  }, []);

  return {
    currentUser,
    refreshCurrentUser,
    resetCurrentUser,
  };
}
