import api from "./api";

export async function listProjectFiles(projectId) {
  const { data } = await api.get(`/projects/${projectId}/files`);
  return data;
}

export async function getProjectFile(projectId, fileId) {
  const { data } = await api.get(`/projects/${projectId}/files/${fileId}`);
  return data;
}

export async function createProjectFile(projectId, path, content) {
  const { data } = await api.post(`/projects/${projectId}/files`, {
    path,
    content,
  });
  return data;
}

export async function updateProjectFile(projectId, fileId, path, content) {
  const { data } = await api.patch(
    `/projects/${projectId}/files/${fileId}`,
    { path, content }
  );
  return data;
}

export async function deleteProjectFile(projectId, fileId) {
  await api.delete(`/projects/${projectId}/files/${fileId}`);
}
