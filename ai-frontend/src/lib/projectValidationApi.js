import api from "./api";

export async function validateProject(projectId) {
  const { data } = await api.get(`/projects/${projectId}/validate`);
  return data;
}
