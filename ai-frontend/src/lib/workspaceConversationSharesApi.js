import api from "./api";

export async function getConversationWorkspaceShare(conversationId) {
  const { data } = await api.get(
    `/conversations/${conversationId}/workspace-share`
  );
  return data;
}

export async function shareConversationWithWorkspace(conversationId) {
  const { data } = await api.post(
    `/conversations/${conversationId}/workspace-share`
  );
  return data;
}

export async function unshareConversationFromWorkspace(conversationId) {
  await api.delete(`/conversations/${conversationId}/workspace-share`);
}

export async function listWorkspaceSharedConversations(workspaceId) {
  const { data } = await api.get(
    `/workspaces/${workspaceId}/shared-conversations`
  );
  return data;
}

export async function getWorkspaceSharedConversation(workspaceId, conversationId) {
  const { data } = await api.get(
    `/workspaces/${workspaceId}/shared-conversations/${conversationId}`
  );
  return data;
}
