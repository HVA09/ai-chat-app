import api from "./api";

export async function listWorkspaces() {
  const { data } = await api.get("/workspaces");
  return data;
}

export async function createWorkspace(name) {
  const { data } = await api.post("/workspaces", { name });
  return data;
}

export async function renameWorkspace(id, name) {
  const { data } = await api.patch(`/workspaces/${id}`, { name });
  return data;
}

export async function updateWorkspaceDefaultModel(id, model) {
  const { data } = await api.patch(`/workspaces/${id}/model`, {
    model: model || null,
  });
  return data;
}
