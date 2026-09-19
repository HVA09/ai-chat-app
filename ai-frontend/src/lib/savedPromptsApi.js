import api from "./api";

export async function listSavedPrompts() {
  const { data } = await api.get("/saved-prompts");
  return data;
}

export async function createSavedPrompt(name, content) {
  const { data } = await api.post("/saved-prompts", { name, content });
  return data;
}

export async function updateSavedPrompt(id, name, content) {
  const { data } = await api.patch(`/saved-prompts/${id}`, { name, content });
  return data;
}

export async function deleteSavedPrompt(id) {
  await api.delete(`/saved-prompts/${id}`);
}
