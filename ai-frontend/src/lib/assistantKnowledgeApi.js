import api from "./api";

export async function listAssistantKnowledgeFiles(assistantId) {
  const { data } = await api.get(`/assistants/${assistantId}/files`);
  return data;
}

export async function attachFileToAssistant(assistantId, fileId) {
  const { data } = await api.post(
    `/assistants/${assistantId}/files/${fileId}`
  );
  return data;
}

export async function detachFileFromAssistant(assistantId, fileId) {
  await api.delete(`/assistants/${assistantId}/files/${fileId}`);
}
