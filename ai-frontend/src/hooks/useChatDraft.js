import { useCallback, useEffect, useRef, useState } from "react";
import { loadChatDraft, saveChatDraft } from "../lib/chatDrafts";

export default function useChatDraft({ authed, userId, conversationId }) {
  const [input, setInput] = useState("");
  const draftHydratedRef = useRef(false);
  const draftSaveTimerRef = useRef(null);

  useEffect(() => {
    if (!authed || !userId || typeof window === "undefined") return;

    draftHydratedRef.current = false;
    setInput(loadChatDraft(userId, conversationId));

    const frame = window.requestAnimationFrame(() => {
      draftHydratedRef.current = true;
    });

    return () => {
      window.cancelAnimationFrame(frame);
    };
  }, [authed, userId, conversationId]);

  useEffect(() => {
    if (!authed || !userId || !draftHydratedRef.current) return;

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
  }, [authed, userId, conversationId, input]);

  const resetChatDraft = useCallback(() => {
    if (draftSaveTimerRef.current) {
      window.clearTimeout(draftSaveTimerRef.current);
      draftSaveTimerRef.current = null;
    }
    draftHydratedRef.current = false;
    setInput("");
  }, []);

  return {
    input,
    setInput,
    resetChatDraft,
  };
}
