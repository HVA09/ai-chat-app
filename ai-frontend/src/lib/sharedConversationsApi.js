import api from "./api";

export async function createConversationShare(conversationId, expiresInDays = 7) {
  const { data } = await api.post(`/conversations/${conversationId}/share`, {
    expires_in_days: expiresInDays,
  });
  return data;
}

export async function revokeConversationShare(conversationId, shareId) {
  await api.delete(`/conversations/${conversationId}/share/${shareId}`);
}

export async function getSharedConversation(token) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const response = await fetch(
    `${baseUrl}/shared-conversations/${encodeURIComponent(token)}`
  );
  if (!response.ok) {
    const error = new Error("shared_conversation_error");
    error.status = response.status;
    throw error;
  }
  return response.json();
}
