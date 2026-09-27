export const API_VERSION = "v1";

export class AIChatError extends Error {
  constructor(message, { statusCode = null, requestId = null, retryAfter = null } = {}) {
    super(message);
    this.name = "AIChatError";
    this.statusCode = statusCode;
    this.requestId = requestId;
    this.retryAfter = retryAfter;
  }
}

export class AuthenticationError extends AIChatError {
  constructor(message, metadata = {}) {
    super(message, metadata);
    this.name = "AuthenticationError";
  }
}

export class RateLimitError extends AIChatError {
  constructor(message, metadata = {}) {
    super(message, metadata);
    this.name = "RateLimitError";
  }
}

export class ValidationError extends AIChatError {
  constructor(message, metadata = {}) {
    super(message, metadata);
    this.name = "ValidationError";
  }
}

export class APIError extends AIChatError {
  constructor(message, metadata = {}) {
    super(message, metadata);
    this.name = "APIError";
  }
}

export class ChatResponse {
  constructor({ conversation_id, reply, model }) {
    this.conversationId = Number(conversation_id);
    this.reply = String(reply);
    this.model = String(model);
  }

  toJSON() {
    return {
      conversation_id: this.conversationId,
      reply: this.reply,
      model: this.model,
    };
  }
}

export class AIChatClient {
  constructor(
    apiKey,
    {
      baseUrl = "https://api.example.com/v1",
      timeoutMs = 30000,
      fetchImpl = globalThis.fetch,
    } = {},
  ) {
    if (!apiKey || !apiKey.trim()) {
      throw new TypeError("apiKey is required");
    }
    if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) {
      throw new TypeError("timeoutMs must be greater than 0");
    }
    if (typeof fetchImpl !== "function") {
      throw new TypeError("A fetch implementation is required");
    }

    const normalized = baseUrl.replace(/\/+$/, "");
    if (!normalized.endsWith("/v1")) {
      throw new TypeError("baseUrl must point to the Developer API v1 namespace");
    }

    this.apiKey = apiKey.trim();
    this.baseUrl = normalized;
    this.timeoutMs = timeoutMs;
    this.fetchImpl = fetchImpl;
  }

  async chat(
    message,
    { conversationId, workspaceId, assistantId, model } = {},
  ) {
    if (!message || !message.trim()) {
      throw new TypeError("message is required");
    }

    const body = { message: message.trim() };
    if (conversationId !== undefined && conversationId !== null) {
      body.conversation_id = conversationId;
    }
    if (workspaceId !== undefined && workspaceId !== null) {
      body.workspace_id = workspaceId;
    }
    if (assistantId !== undefined && assistantId !== null) {
      body.assistant_id = assistantId;
    }
    if (model !== undefined && model !== null && String(model).trim()) {
      body.model = String(model).trim();
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);

    let response;
    try {
      response = await this.fetchImpl(`${this.baseUrl}/chat`, {
        method: "POST",
        headers: {
          "X-API-Key": this.apiKey,
          Accept: "application/json",
          "Content-Type": "application/json",
          "User-Agent": "ai-chat-saas-javascript/0.1.0",
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
    } catch (error) {
      throw new APIError(
        error?.name === "AbortError"
          ? "Developer API request timed out."
          : "Developer API request failed.",
        {},
      );
    } finally {
      clearTimeout(timeout);
    }

    const requestId = response.headers.get("X-Request-ID");
    const retryAfter = response.headers.get("Retry-After");

    if (!response.ok) {
      const messageText = await this.#errorMessage(response);
      const metadata = {
        statusCode: response.status,
        requestId,
        retryAfter,
      };
      if (response.status === 401) {
        throw new AuthenticationError(messageText, metadata);
      }
      if (response.status === 422) {
        throw new ValidationError(messageText, metadata);
      }
      if (response.status === 429) {
        throw new RateLimitError(messageText, metadata);
      }
      throw new APIError(messageText, metadata);
    }

    let payload;
    try {
      payload = await response.json();
    } catch (error) {
      throw new APIError("Developer API returned invalid JSON.", {
        statusCode: response.status,
        requestId,
      });
    }

    try {
      return new ChatResponse(payload);
    } catch (error) {
      throw new APIError("Developer API returned an invalid response payload.", {
        statusCode: response.status,
        requestId,
      });
    }
  }

  async #errorMessage(response) {
    try {
      const payload = await response.json();
      if (payload && typeof payload === "object") {
        if (payload.detail) return String(payload.detail);
        if (payload.message) return String(payload.message);
      }
    } catch {
      // Fall back to the HTTP status text below.
    }
    return `Developer API error (${response.status}).`;
  }
}
