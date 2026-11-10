import api from "./api";
import { detailToMessage } from "./errors";
import i18n from "../i18n";

export async function sendChatMessage(
  message,
  conversationId = null,
  assistantId = null,
  workspaceId = null,
  projectId = null,
  model = null,
  fileIds = []
) {
  const { data } = await api.post("/chat", {
    message,
    conversation_id: conversationId,
    assistant_id: assistantId,
    workspace_id: workspaceId,
    project_id: projectId,
    model,
    file_ids: fileIds,
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
  assistantId = null,
  {
    onChunk,
    onConversationId,
    onSources,
    onToolEvent,
    onDone,
    onError,
    signal,
    workspaceId = null,
    projectId = null,
    model = null,
    fileIds = [],
  } = {}
) {
  const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const isAgentRequest =
    typeof message === "string" && /^(?:\/agent|\/run)(?:\s|$)/.test(message.trim());
  const agentInterruptedMessage = i18n.language?.toLowerCase().startsWith("en")
    ? "The Agent connection ended before completion. A tool may have run or the request may still be processing. Automatic retry is disabled to avoid repeating side effects; check the result before continuing."
    : "انقطع الاتصال قبل اكتمال مهمة الوكيل. ربما بدأت أداة التنفيذ أو ما زال الطلب قيد المعالجة. أوقفنا إعادة المحاولة التلقائية لتجنب تكرار العمليات؛ تحقق من الحالة قبل المتابعة.";
  const reportInterruptedAgent = () =>
    onError?.(agentInterruptedMessage, {
      kind: "transport",
      messagePersisted: false,
      retryMode: "blocked",
    });

  let toolExecutionStarted = false;
  let terminalEventReceived = false;
  let messagePersisted = true;
  let retryMode = null;
  let response;
  try {
    response = await fetch(`${baseURL}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": i18n.language,
      },
      credentials: "include",
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        assistant_id: assistantId,
        workspace_id: workspaceId,
        project_id: projectId,
        model,
        file_ids: fileIds,
      }),
      signal,
    });
  } catch (err) {
    if (err?.name === "AbortError") {
      if (isAgentRequest) reportInterruptedAgent();
      else onDone?.();
      return;
    }
    if (isAgentRequest) reportInterruptedAgent();
    else onError?.(i18n.t("app.connectionError"), { kind: "transport", messagePersisted: false });
    return;
  }

  if (!response.ok) {
    if (response.status === 401) {
      window.dispatchEvent(new Event("auth:unauthorized"));
      return;
    }
    const body = await response.json().catch(() => ({}));
    onError?.(detailToMessage(body.detail, i18n.t("app.sendMessageError")), {
      kind: "http",
      status: response.status,
      messagePersisted: false,
    });
    return;
  }

  // The normal chat route persists the user message before streaming. The agent
  // branch is different: it persists only after the agent succeeds, so the server
  // can explicitly mark an error as safe to resend.
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
        else if (eventType === "sources") onSources?.(JSON.parse(data));
        else if (eventType === "tool") {
          const toolEvent = JSON.parse(data);
          if (isAgentRequest && toolEvent?.type === "start") toolExecutionStarted = true;
          onToolEvent?.(toolEvent);
        }
        else if (eventType === "retry_mode") {
          retryMode = isAgentRequest && toolExecutionStarted && data === "send"
            ? "blocked"
            : data;
          messagePersisted = retryMode !== "send" && retryMode !== "blocked";
        }
        else if (eventType === "chunk") onChunk?.(data.replace(/\\n/g, "\n"));
        else if (eventType === "error") {
          terminalEventReceived = true;
          const effectiveRetryMode = isAgentRequest
            ? (toolExecutionStarted || retryMode !== "send" ? "blocked" : "send")
            : retryMode;
          if (effectiveRetryMode) {
            retryMode = effectiveRetryMode;
            messagePersisted = effectiveRetryMode !== "send" && effectiveRetryMode !== "blocked";
          }
          onError?.(data, {
            kind: "stream",
            messagePersisted,
            ...(retryMode ? { retryMode } : {}),
          });
        }
        else if (eventType === "done") {
          terminalEventReceived = true;
          onDone?.();
        }
      }
    }
    if (isAgentRequest && !terminalEventReceived) reportInterruptedAgent();
  } catch (err) {
    if (err?.name === "AbortError") {
      try {
        await reader.cancel();
      } catch {
        /* ignore */
      }
      if (isAgentRequest) reportInterruptedAgent();
      else onDone?.();
      return;
    }
    if (isAgentRequest) reportInterruptedAgent();
    else onError?.(i18n.t("app.connectionError"), { kind: "transport", messagePersisted: true });
  }
}

/**
 * إعادة توليد آخر رد للمحادثة مع نفس أسلوب البث التدريجي.
 * لا ترسل رسالة مستخدم جديدة، حتى لا تتكرر الرسالة في سجل المحادثة.
 */
export async function streamRegenerateMessage(
  conversationId,
  { onChunk, onConversationId, onSources, onDone, onError, signal } = {}
) {
  const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  let response;
  try {
    response = await fetch(`${baseURL}/chat/${conversationId}/regenerate/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": i18n.language,
      },
      credentials: "include",
      body: JSON.stringify({}),
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

/**
 * تعديل رسالة مستخدم سابقة مع إعادة توليد كل ما بعدها، بدون إضافة رسالة مستخدم جديدة.
 * messageIndex يبدأ من 1 بين رسائل المستخدم داخل المحادثة.
 */
export async function streamEditMessage(
  conversationId,
  messageIndex,
  message,
  { onChunk, onConversationId, onSources, onDone, onError, signal } = {}
) {
  const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  let response;
  try {
    response = await fetch(`${baseURL}/chat/${conversationId}/edit/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": i18n.language,
      },
      credentials: "include",
      body: JSON.stringify({ message_index: messageIndex, message }),
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


export async function setMessageFeedback(conversationId, messageIndex, rating) {
  const { data } = await api.patch(
    `/chat/${conversationId}/messages/${messageIndex}/feedback`,
    { rating }
  );
  return data;
}


export async function analyzeImage(conversationId, fileId, message) {
  const { data } = await api.post("/chat/vision", {
    conversation_id: conversationId,
    file_id: fileId,
    message,
  });
  return data;
}


export async function listAiModels() {
  const { data } = await api.get("/chat/models");
  return data;
}


export async function compareChatModels(payload) {
  const { data } = await api.post("/chat/compare", payload);
  return data;
}
