import api from "./api";

export async function listConversationComments(workspaceId, conversationId) {
  const { data } = await api.get(
    `/workspaces/${workspaceId}/shared-conversations/${conversationId}/comments`
  );
  return data;
}

export async function createConversationComment(
  workspaceId,
  conversationId,
  content,
  messageId = null
) {
  const payload = { content };
  if (messageId !== null && messageId !== undefined) {
    payload.message_id = messageId;
  }
  const { data } = await api.post(
    `/workspaces/${workspaceId}/shared-conversations/${conversationId}/comments`,
    payload
  );
  return data;
}

export async function updateConversationComment(
  workspaceId,
  conversationId,
  commentId,
  content
) {
  const { data } = await api.patch(
    `/workspaces/${workspaceId}/shared-conversations/${conversationId}/comments/${commentId}`,
    { content }
  );
  return data;
}

export async function deleteConversationComment(
  workspaceId,
  conversationId,
  commentId
) {
  await api.delete(
    `/workspaces/${workspaceId}/shared-conversations/${conversationId}/comments/${commentId}`
  );
}
