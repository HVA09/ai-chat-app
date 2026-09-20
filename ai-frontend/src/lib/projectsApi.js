import api from "./api";

export async function listProjects(workspaceId) {
  const { data } = await api.get("/projects", {
    params: { workspace_id: workspaceId },
  });
  return data;
}

export async function createProject(workspaceId, name, description = "") {
  const { data } = await api.post("/projects", {
    workspace_id: workspaceId,
    name,
    description: description || null,
  });
  return data;
}

export async function updateProject(id, name, description = "") {
  const { data } = await api.patch(`/projects/${id}`, {
    name,
    description: description || null,
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
