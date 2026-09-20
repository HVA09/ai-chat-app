import api from "./api";

export async function listFolders() {
  const { data } = await api.get("/folders");
  return data;
}

export async function createFolder(name) {
  const { data } = await api.post("/folders", { name });
  return data;
}

export async function renameFolder(id, name) {
  const { data } = await api.patch(`/folders/${id}`, { name });
  return data;
}

export async function deleteFolder(id) {
  await api.delete(`/folders/${id}`);
}

