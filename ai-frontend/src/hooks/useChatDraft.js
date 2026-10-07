import { useCallback, useEffect, useRef, useState } from "react";
import { loadChatDraft, saveChatDraft } from "../lib/chatDrafts";

export default function useChatDraft({ authed, userId, conversationId }) {
  const [input, setInput] = useState("");
  const [draftHydrated, setDraftHydrated] = useState(false);
  const draftSaveTimerRef = useRef(null);

  useEffect(() => {
    if (!authed || !userId || typeof window === "undefined") return;

    setDraftHydrated(false);
    setInput(loadChatDraft(userId, conversationId));

    const frame = window.requestAnimationFrame(() => {
      setDraftHydrated(true);
    });

    return () => {
      window.cancelAnimationFrame(frame);
    };
  }, [authed, userId, conversationId]);

  useEffect(() => {
    if (!authed || !userId || !draftHydrated) return;

    if (draftSaveTimerRef.current) {
      window.clearTimeout(draftSaveTimerRef.current);
    }

    draftSaveTimerRef.current = window.setTimeout(() => {
      saveChatDraft(userId, conversationId, input);
      draftSaveTimerRef.current = null;
    }, 300);

    return () => {
      if (draftSaveTimerRef.current) {
        window.clearTimeout(draftSaveTimerRef.current);
      }
    };
  }, [authed, userId, conversationId, input, draftHydrated]);

  const resetChatDraft = useCallback(() => {
    if (draftSaveTimerRef.current) {
      window.clearTimeout(draftSaveTimerRef.current);
      draftSaveTimerRef.current = null;
    }
    setDraftHydrated(false);
    setInput("");
  }, []);

  return {
    input,
    setInput,
    resetChatDraft,
  };
}
