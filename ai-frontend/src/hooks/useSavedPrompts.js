import { useCallback, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createSavedPrompt,
  deleteSavedPrompt,
  listSavedPrompts,
  updateSavedPrompt,
} from "../lib/savedPromptsApi";
import { getErrorMessage } from "../lib/errors";

export default function useSavedPrompts({ setToast }) {
  const { t } = useTranslation();
  const [savedPrompts, setSavedPrompts] = useState([]);
  const refreshRequestRef = useRef(0);

  const resetSavedPrompts = useCallback(() => {
    // Invalidate any request started before logout or account reset.
    refreshRequestRef.current += 1;
    setSavedPrompts([]);
  }, []);

  const refreshSavedPrompts = useCallback(async () => {
    const requestId = ++refreshRequestRef.current;
    try {
      const prompts = await listSavedPrompts();
      if (requestId !== refreshRequestRef.current) return;
      setSavedPrompts(prompts);
    } catch (err) {
      // A stale failure should not show an error for a newer session or refresh.
      if (requestId !== refreshRequestRef.current) return;
      setToast({
        message: getErrorMessage(err, t("app.savedPromptsLoadError")),
        type: "error",
      });
    }
  }, [setToast, t]);

  const handleCreateSavedPrompt = useCallback(async () => {
    const name = window.prompt(t("sidebar.savedPromptCreateNamePrompt"));
    if (!name?.trim()) return;
    const content = window.prompt(t("sidebar.savedPromptCreateContentPrompt"));
    if (!content?.trim()) return;

    try {
      await createSavedPrompt(name.trim(), content.trim());
      await refreshSavedPrompts();
    } catch (err) {
      setToast({
        message:
          err?.response?.data?.detail ||
          t("app.savedPromptCreateError"),
        type: "error",
      });
    }
  }, [refreshSavedPrompts, setToast, t]);

  const handleRenameSavedPrompt = useCallback(
    async (id, currentName, currentContent) => {
      const name = window.prompt(
        t("sidebar.savedPromptRenameNamePrompt"),
        currentName
      );
      if (!name?.trim()) return;

      const content = window.prompt(
        t("sidebar.savedPromptRenameContentPrompt"),
        currentContent
      );
      if (!content?.trim()) return;

      try {
        await updateSavedPrompt(id, name.trim(), content.trim());
        await refreshSavedPrompts();
      } catch (err) {
        setToast({
          message:
            err?.response?.data?.detail ||
            t("app.savedPromptUpdateError"),
          type: "error",
        });
      }
    },
    [refreshSavedPrompts, setToast, t]
  );

  const handleDeleteSavedPrompt = useCallback(
    async (id, name) => {
      if (!window.confirm(t("sidebar.savedPromptDeleteConfirm", { name }))) {
        return;
      }

      try {
        await deleteSavedPrompt(id);
        await refreshSavedPrompts();
      } catch (err) {
        setToast({
          message:
            err?.response?.data?.detail ||
            t("app.savedPromptDeleteError"),
          type: "error",
        });
      }
    },
    [refreshSavedPrompts, setToast, t]
  );

  return {
    savedPrompts,
    resetSavedPrompts,
    refreshSavedPrompts,
    handleCreateSavedPrompt,
    handleRenameSavedPrompt,
    handleDeleteSavedPrompt,
  };
}
