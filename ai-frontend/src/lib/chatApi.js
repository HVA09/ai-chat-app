import api from "./api";
import { detailToMessage } from "./errors";
import i18n from "../i18n";

export async function sendChatMessage(message, conversationId = null) {
  const { data } = await api.post("/chat", {
    message,
    conversation_id: conversationId,
  });
  return data;
}

/**
 * إرسال رسالة مع استقبال الرد تدريجيًا (streaming) عبر Server-Sent Events.
 * يدعم signal (AbortController) لإيقاف التوليد من الواجهة.
 */
export async function streamChatMessage(
  message,
  conversationId,
  { onChunk, onConversationId, onDone, onError, signal } = {}
) {
  const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  let response;
  try {
    response = await fetch(`${baseURL}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({ message, conversation_id: conversationId }),
      signal,
    });
  } catch (err) {
    if (err?.name === "AbortError") {
      onDone?.();
      return;
    }
    onError?.(i18n.t("app.connectionError"));
    return;
  }

  if (!response.ok) {
    if (response.status === 401) {
      window.dispatchEvent(new Event("auth:unauthorized"));
      return;
    }
    const body = await response.json().catch(() => ({}));
    onError?.(detailToMessage(body.detail, i18n.t("app.sendMessageError")));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";

      for (const raw of events) {
        const lines = raw.split("\n");
        const eventLine = lines.find((l) => l.startsWith("event: "));
        const dataLine = lines.find((l) => l.startsWith("data: "));
        if (!eventLine || !dataLine) continue;

        const eventType = eventLine.slice("event: ".length);
        const data = dataLine.slice("data: ".length);

        if (eventType === "conversation") onConversationId?.(Number(data));
        else if (eventType === "chunk") onChunk?.(data.replace(/\\n/g, "\n"));
        else if (eventType === "error") onError?.(data);
        else if (eventType === "done") onDone?.();
      }
    }
  } catch (err) {
    if (err?.name === "AbortError") {
      try {
        await reader.cancel();
      } catch {
        /* ignore */
      }
      onDone?.();
      return;
    }
    throw err;
  }
}
