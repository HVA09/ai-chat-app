import api from "./api";

export async function uploadFile(
  file,
  onProgress,
  conversationId = null,
  workspaceId = null,
  projectId = null
) {
  const formData = new FormData();
  formData.append("file", file);
  const params = {};
  if (conversationId) params.conversation_id = conversationId;
  if (workspaceId) params.workspace_id = workspaceId;
  if (projectId) params.project_id = projectId;
  const { data } = await api.post("/files/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    params,
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    },
  });
  return data;
}

export async function listFiles(
  conversationId = null,
  includeUnattached = false,
  workspaceId = null,
  projectId = null
) {
  const params = {};
  if (conversationId) {
    params.conversation_id = conversationId;
    params.include_unattached = includeUnattached;
  }
  if (workspaceId) params.workspace_id = workspaceId;
  if (projectId) params.project_id = projectId;
  const { data } = await api.get("/files", { params });
  return data;
}

export async function deleteFile(id) {
  await api.delete(`/files/${id}`);
}

// التحميل يحتاج نفس هيدر الـ Authorization، ورابط <a> عادي ما يقدر يرسله —
// فنجيب الملف كـ blob عبر axios (اللي يرفق التوكن تلقائيًا) وننزّله يدويًا
export async function fetchFileBlob(id) {
  const response = await api.get(`/files/${id}`, { responseType: "blob" });
  return response.data;
}

export async function downloadFile(id, filename) {
  const blob = await fetchFileBlob(id);
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}


export async function attachFileToConversation(fileId, conversationId) {
  const { data } = await api.post(`/files/${fileId}/attach/${conversationId}`);
  return data;
}

export async function detachFileFromConversation(fileId, conversationId) {
  await api.delete(`/files/${fileId}/attach/${conversationId}`);
}


export async function indexImageForRag(id) {
  const { data } = await api.post(`/files/${id}/index-image`);
  return data;
}
