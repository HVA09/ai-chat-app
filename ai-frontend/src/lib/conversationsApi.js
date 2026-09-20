import api from "./api";

export async function listConversations(includeArchived = false, folderId = null) {
  const params = { include_archived: includeArchived };
  if (folderId !== null && folderId !== undefined) {
    params.folder_id = folderId;
  }
  const { data } = await api.get("/conversations", { params });
  return data;
}

export async function getConversation(id) {
  const { data } = await api.get(`/conversations/${id}`);
  return data;
}

export async function renameConversation(id, title) {
  const { data } = await api.patch(`/conversations/${id}`, { title });
  return data;
}

export async function deleteConversation(id) {
  await api.delete(`/conversations/${id}`);
}

export async function togglePinConversation(id) {
  const { data } = await api.patch(`/conversations/${id}/pin`);
  return data;
}

export async function toggleArchiveConversation(id) {
  const { data } = await api.patch(`/conversations/${id}/archive`);
  return data;
}

export async function moveConversationToFolder(id, folderId) {
  const { data } = await api.patch(`/conversations/${id}/folder`, {
    folder_id: folderId,
  });
  return data;
}
