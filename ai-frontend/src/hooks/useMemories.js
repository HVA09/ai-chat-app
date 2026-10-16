import { useCallback, useEffect, useRef, useState } from "react";
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
  const sessionEpochRef = useRef(0);
  const refreshRequestRef = useRef(0);

  const refreshMemories = useCallback(async () => {
    const sessionEpoch = sessionEpochRef.current;
    const requestId = ++refreshRequestRef.current;
    try {
      const nextMemories = await listMemories();
      if (
        sessionEpoch !== sessionEpochRef.current ||
        requestId !== refreshRequestRef.current
      ) {
        return;
      }
      setMemories(nextMemories);
    } catch (err) {
      // Ignore errors from an old session or a refresh superseded by a newer one.
      if (
        sessionEpoch !== sessionEpochRef.current ||
        requestId !== refreshRequestRef.current
      ) {
        return;
      }
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
      const sessionEpoch = sessionEpochRef.current;

      try {
        if (existing) {
          await deleteMemory(existing.id);
          if (sessionEpoch !== sessionEpochRef.current) return;

          setMemories((current) =>
            current.filter((memory) => memory.id !== existing.id)
          );
          setToast({ message: t("memory.removed"), type: "success" });
          return;
        }

        const created = await createMemory(content);
        if (sessionEpoch !== sessionEpochRef.current) return;

        setMemories((current) => [created, ...current]);
        setToast({ message: t("memory.saved"), type: "success" });
      } catch (err) {
        if (sessionEpoch !== sessionEpochRef.current) return;
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
    // Invalidate pending reads and mutations before clearing account state.
    sessionEpochRef.current += 1;
    refreshRequestRef.current += 1;
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
