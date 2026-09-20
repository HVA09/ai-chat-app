import api from "./api";

export async function listFolders(workspaceId = null) {
  const params = {};
  if (workspaceId !== null && workspaceId !== undefined) {
    params.workspace_id = workspaceId;
  }
  const { data } = await api.get("/folders", { params });
  return data;
}

export async function createFolder(name, workspaceId = null) {
  const payload = { name };
  if (workspaceId !== null && workspaceId !== undefined) {
    payload.workspace_id = workspaceId;
  }
  const { data } = await api.post("/folders", payload);
  return data;
}

export async function renameFolder(id, name) {
  const { data } = await api.patch(`/folders/${id}`, { name });
  return data;
}

export async function deleteFolder(id) {
  await api.delete(`/folders/${id}`);
}

export async function moveConversationToFolder(conversationId, folderId) {
  const { data } = await api.patch(`/conversations/${conversationId}/folder`, {
    folder_id: folderId,
  });
  return data;
}
