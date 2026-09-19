import api from "./api";

export async function listMemories() {
  const { data } = await api.get("/memories");
  return data;
}

export async function createMemory(content) {
  const { data } = await api.post("/memories", { content });
  return data;
}

export async function updateMemory(id, content) {
  const { data } = await api.patch(`/memories/${id}`, { content });
  return data;
}

export async function deleteMemory(id) {
  await api.delete(`/memories/${id}`);
}
