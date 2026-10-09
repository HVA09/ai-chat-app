import { useCallback } from "react";

export default function useAppendToLastMessage({ setMessages }) {
  return useCallback(
    (chunk) => {
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        next[next.length - 1] = { ...last, text: last.text + chunk };
        return next;
      });
    },
    [setMessages]
  );
}
