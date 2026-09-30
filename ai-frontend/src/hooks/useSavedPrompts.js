import { useCallback, useState } from "react";
import { useAppDialog } from "../components/AppDialog";
import { useTranslation } from "react-i18next";
import {
  createSavedPrompt,
  deleteSavedPrompt,
  listSavedPrompts,
  updateSavedPrompt,
} from "../lib/savedPromptsApi";

export default function useSavedPrompts({ setToast }) {
  const { t } = useTranslation();
  const { confirm, prompt } = useAppDialog();
  const [savedPrompts, setSavedPrompts] = useState([]);

  const resetSavedPrompts = useCallback(() => setSavedPrompts([]), []);

  const refreshSavedPrompts = useCallback(async () => {
    try {
      setSavedPrompts(await listSavedPrompts());
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.savedPromptsLoadError"),
        type: "error",
      });
    }
  }, [setToast, t]);

  const handleCreateSavedPrompt = useCallback(async () => {
    const name = await prompt({
      title: t("sidebar.savedPromptCreateNamePrompt"),
      message: t("sidebar.savedPromptCreateNamePrompt"),
    });
    if (!name?.trim()) return;
    const content = await prompt({
      title: t("sidebar.savedPromptCreateContentPrompt"),
      message: t("sidebar.savedPromptCreateContentPrompt"),
      multiline: true,
      maxLength: 4000,
    });
    if (!content?.trim()) return;

    try {
      await createSavedPrompt(name.trim(), content.trim());
      await refreshSavedPrompts();
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("app.savedPromptCreateError"),
        type: "error",
      });
    }
  }, [prompt, refreshSavedPrompts, setToast, t]);

  const handleRenameSavedPrompt = useCallback(
    async (id, currentName, currentContent) => {
      const name = await prompt({
        title: t("sidebar.savedPromptRenameNamePrompt"),
        message: t("sidebar.savedPromptRenameNamePrompt"),
        defaultValue: currentName,
      });
      if (!name?.trim()) return;

      const content = await prompt({
        title: t("sidebar.savedPromptRenameContentPrompt"),
        message: t("sidebar.savedPromptRenameContentPrompt"),
        defaultValue: currentContent,
        multiline: true,
        maxLength: 4000,
      });
      if (!content?.trim()) return;

      try {
        await updateSavedPrompt(id, name.trim(), content.trim());
        await refreshSavedPrompts();
      } catch (err) {
        setToast({
          message: err?.response?.data?.detail || t("app.savedPromptUpdateError"),
          type: "error",
        });
      }
    },
    [prompt, refreshSavedPrompts, setToast, t]
  );

  const handleDeleteSavedPrompt = useCallback(
    async (id, name) => {
      const confirmed = await confirm({
        title: t("sidebar.savedPromptDeleteConfirm", { name }),
        message: t("sidebar.savedPromptDeleteConfirm", { name }),
      });
      if (!confirmed) return;

      try {
        await deleteSavedPrompt(id);
        await refreshSavedPrompts();
      } catch (err) {
        setToast({
          message: err?.response?.data?.detail || t("app.savedPromptDeleteError"),
          type: "error",
        });
      }
    },
    [confirm, refreshSavedPrompts, setToast, t]
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
