import api from "./api";

export async function listAssistants() {
  const { data } = await api.get("/assistants");
  return data;
}

export async function createAssistant({ name, description, instructions }) {
  const { data } = await api.post("/assistants", {
    name,
    description,
    instructions,
  });
  return data;
}

export async function updateAssistant(id, payload) {
  const { data } = await api.patch(`/assistants/${id}`, payload);
  return data;
}

export async function deleteAssistant(id) {
  await api.delete(`/assistants/${id}`);
}

export async function listWorkspaceSharedAssistants(workspaceId) {
  const { data } = await api.get(`/workspaces/${workspaceId}/shared-assistants`);
  return data;
}

export async function shareAssistantWithWorkspace(assistantId, workspaceId) {
  const { data } = await api.post(
    `/assistants/${assistantId}/workspace-share/${workspaceId}`
  );
  return data;
}

export async function unshareAssistantFromWorkspace(assistantId, workspaceId) {
  await api.delete(
    `/assistants/${assistantId}/workspace-share/${workspaceId}`
  );
}
