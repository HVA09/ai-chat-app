import api from "./api";

export async function listAssistantVersions(assistantId) {
  const { data } = await api.get(`/assistants/${assistantId}/versions`);
  return data;
}

export async function restoreAssistantVersion(assistantId, version) {
  const { data } = await api.post(
    `/assistants/${assistantId}/versions/${version}/restore`
  );
  return data;
}
