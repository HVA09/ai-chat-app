import api from "./api";

export async function createConversationShare(
  conversationId,
  expiresInDays = 7,
  password = null
) {
  const payload = { expires_in_days: expiresInDays };
  if (password) payload.password = password;

  const { data } = await api.post(
    `/conversations/${conversationId}/share`,
    payload
  );
  return data;
}

export async function listConversationShares(conversationId) {
  const { data } = await api.get(`/conversations/${conversationId}/shares`);
  return data;
}

export async function revokeConversationShare(conversationId, shareId) {
  await api.delete(`/conversations/${conversationId}/share/${shareId}`);
}

async function parseSharedConversationError(response) {
  const body = await response.json().catch(() => ({}));
  const error = new Error(body.detail || "shared_conversation_error");
  error.status = response.status;
  error.detail = body.detail || "";
  return error;
}

export async function getSharedConversation(token) {
  const baseUrl =
    import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const response = await fetch(
    `${baseUrl}/shared-conversations/${encodeURIComponent(token)}`
  );
  if (!response.ok) {
    throw await parseSharedConversationError(response);
  }
  return response.json();
}

export async function accessProtectedSharedConversation(token, password) {
  const baseUrl =
    import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const response = await fetch(
    `${baseUrl}/shared-conversations/${encodeURIComponent(token)}/access`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    }
  );
  if (!response.ok) {
    throw await parseSharedConversationError(response);
  }
  return response.json();
}
