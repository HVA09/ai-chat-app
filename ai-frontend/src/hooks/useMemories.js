import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { createMemory, deleteMemory, listMemories } from "../lib/memoriesApi";
import { getErrorMessage } from "../lib/errors";

export default function useMemories({ setToast, messages, readOnlyConversation, loading, editingMessageIndex }) {
  const { t } = useTranslation();
  const [memories, setMemories] = useState([]);

  const refreshMemories = useCallback(async () => {
    try {
      setMemories(await listMemories());
    } catch (err) {
      setToast({
        message: getErrorMessage(err, t("app.memoriesLoadError")),
        type: "error",
      });
    }
  }, [setToast, t]);

  const handleToggleMessageMemory = useCallback(async (index) => {
    if (
      readOnlyConversation ||
      loading ||
      editingMessageIndex !== null ||
      messages[index]?.role !== "user"
    ) return;

    const content = messages[index]?.text?.trim();
    if (!content) return;

    const existing = memories.find((memory) => memory.content === content);
    try {
      if (existing) {
        await deleteMemory(existing.id);
        setMemories((current) => current.filter((memory) => memory.id !== existing.id));
        setToast({ message: t("memory.removed"), type: "success" });
      } else {
        const created = await createMemory(content);
        setMemories((current) => [created, ...current]);
        setToast({ message: t("memory.saved"), type: "success" });
      }
    } catch (err) {
      setToast({
        message: err?.response?.data?.detail || t("memory.error"),
        type: "error",
      });
    }
  }, [editingMessageIndex, loading, memories, messages, readOnlyConversation, setToast, t]);

  return { memories, refreshMemories, handleToggleMessageMemory };
}
