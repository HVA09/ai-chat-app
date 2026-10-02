import api from "./api";

export async function listProjects(workspaceId) {
  const { data } = await api.get("/projects", {
    params: { workspace_id: workspaceId },
  });
  return data;
}

export async function createProject(
  workspaceId,
  name,
  description = "",
  instructions = "",
  assistantId = null
) {
  const { data } = await api.post("/projects", {
    workspace_id: workspaceId,
    name,
    description: description || null,
    instructions: instructions || null,
    assistant_id: assistantId ?? null,
  });
  return data;
}

export async function updateProject(
  id,
  name,
  description = "",
  instructions = "",
  assistantId = null
) {
  const { data } = await api.patch(`/projects/${id}`, {
    name,
    description: description || null,
    instructions: instructions || null,
    assistant_id: assistantId ?? null,
  });
  return data;
}

export async function deleteProject(id) {
  await api.delete(`/projects/${id}`);
}

export async function moveConversationToProject(conversationId, projectId) {
  const { data } = await api.patch(`/conversations/${conversationId}/project`, {
    project_id: projectId,
  });
  return data;
}


export async function exportProject(id) {
  const { data } = await api.get(`/projects/${id}/export`, {
    responseType: "blob",
  });
  return data;
}

export async function importProject(workspaceId, file, onConflict = "fail") {
  const formData = new FormData();
  formData.append("workspace_id", String(workspaceId));
  formData.append("on_conflict", onConflict);
  formData.append("archive", file);
  const { data } = await api.post("/projects/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}


export async function listProjectArtifacts(projectId) {
  const { data } = await api.get(`/projects/${projectId}/preview-artifacts`);
  return data;
}

export async function deleteProjectArtifact(projectId, artifactId) {
  await api.delete(`/projects/${projectId}/preview-artifacts/${artifactId}`);
}

export async function cleanupProjectArtifacts(projectId) {
  const { data } = await api.post(
    `/projects/${projectId}/preview-artifacts/cleanup`
  );
  return data;
}
