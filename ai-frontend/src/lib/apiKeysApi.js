import api from "./api";

export async function listApiKeys() {
  const { data } = await api.get("/api-keys");
  return data;
}

export async function createApiKey(name) {
  const { data } = await api.post("/api-keys", { name });
  return data;
}

export async function revokeApiKey(id) {
  await api.delete(`/api-keys/${id}`);
}
