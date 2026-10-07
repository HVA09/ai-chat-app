import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { listMemories, createMemory, deleteMemory } from "../lib/memoriesApi";
import { getErrorMessage } from "../lib/errors";

/**
 * Owns remembered-message state and actions for the active authenticated session.
 *
 * The hook keeps memory persistence behavior outside the root App component while
 * preserving the existing message-content matching and toast semantics.
 */
export default function useMemories({
  authed,
  messages,
  loading,
  readOnlyConversation,
  editingMessageIndex,
  setToast,
}) {
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

  const handleToggleMessageMemory = useCallback(
    async (index) => {
      if (
        readOnlyConversation ||
        loading ||
        editingMessageIndex !== null
      ) {
        return;
      }

      const message = messages[index];
      if (!message || message.role !== "user") return;

      const content = message.text?.trim();
      if (!content) return;

      const existing = memories.find((memory) => memory.content === content);

      try {
        if (existing) {
          await deleteMemory(existing.id);
          setMemories((current) =>
            current.filter((memory) => memory.id !== existing.id)
          );
          setToast({ message: t("memory.removed"), type: "success" });
          return;
        }

        const created = await createMemory(content);
        setMemories((current) => [created, ...current]);
        setToast({ message: t("memory.saved"), type: "success" });
      } catch (err) {
        setToast({
          message: err?.response?.data?.detail || t("memory.error"),
          type: "error",
        });
      }
    },
    [
      editingMessageIndex,
      loading,
      messages,
      memories,
      readOnlyConversation,
      setToast,
      t,
    ]
  );

  const resetMemories = useCallback(() => {
    setMemories([]);
  }, []);

  useEffect(() => {
    if (authed) {
      refreshMemories();
    }
  }, [authed, refreshMemories]);

  return {
    memories,
    refreshMemories,
    handleToggleMessageMemory,
    resetMemories,
  };
}
