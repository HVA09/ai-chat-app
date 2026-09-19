import api from "./api";

export async function listConversations(
  includeArchived = false,
  folderId = null,
  workspaceId = null,
  search = "",
  includeDeleted = false
) {
  const params = {
    include_archived: includeArchived,
    include_deleted: includeDeleted,
  };
  if (folderId !== null && folderId !== undefined) {
    params.folder_id = folderId;
  }
  if (workspaceId !== null && workspaceId !== undefined) {
    params.workspace_id = workspaceId;
  }
  if (search?.trim()) {
    params.search = search.trim();
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

export async function toggleTrashConversation(id) {
  const { data } = await api.patch(`/conversations/${id}/trash`);
  return data;
}

export async function moveConversationToFolder(id, folderId) {
  const { data } = await api.patch(`/conversations/${id}/folder`, {
    folder_id: folderId,
  });
  return data;
}

export async function exportConversation(id, format = "markdown") {
  const response = await api.get(`/conversations/${id}/export`, {
    params: { format },
    responseType: "blob",
  });

  const contentDisposition = response.headers["content-disposition"] || "";
  const match = contentDisposition.match(/filename="([^"]+)"/i);
  const fallbackExtension = format === "json" ? "json" : "md";
  const filename = match?.[1] || `conversation.${fallbackExtension}`;
  const url = URL.createObjectURL(response.data);

  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}
