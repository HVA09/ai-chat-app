import api from "./api";

export async function listProjectMemories(projectId) {
  const { data } = await api.get(`/projects/${projectId}/memories`);
  return data;
}

export async function createProjectMemory(projectId, content) {
  const { data } = await api.post(`/projects/${projectId}/memories`, { content });
  return data;
}

export async function updateProjectMemory(projectId, memoryId, content) {
  const { data } = await api.patch(
    `/projects/${projectId}/memories/${memoryId}`,
    { content }
  );
  return data;
}

export async function deleteProjectMemory(projectId, memoryId) {
  await api.delete(`/projects/${projectId}/memories/${memoryId}`);
}
