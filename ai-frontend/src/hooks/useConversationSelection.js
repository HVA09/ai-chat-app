import { useCallback } from "react";

export default function useConversationSelection({ setSelectedConversationIds }) {
  const toggleConversationSelection = useCallback(
    (id) => {
      setSelectedConversationIds((prev) =>
        prev.includes(id)
          ? prev.filter((itemId) => itemId !== id)
          : [...prev, id]
      );
    },
    [setSelectedConversationIds]
  );

  const toggleSelectAllVisibleConversations = useCallback(
    (ids) => {
      setSelectedConversationIds((prev) => {
        const visible = new Set(ids);
        const allSelected =
          ids.length > 0 && ids.every((id) => prev.includes(id));

        if (allSelected) {
          return prev.filter((id) => !visible.has(id));
        }

        return Array.from(new Set([...prev, ...ids]));
      });
    },
    [setSelectedConversationIds]
  );

  const clearSelectedConversations = useCallback(() => {
    setSelectedConversationIds([]);
  }, [setSelectedConversationIds]);

  return {
    toggleConversationSelection,
    toggleSelectAllVisibleConversations,
    clearSelectedConversations,
  };
}
