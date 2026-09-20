import api from "./api";

export async function listApiKeys() {
  const { data } = await api.get("/api-keys");
  return data;
}

export async function createApiKey(name, dailyRequestLimit = null, expiresAt = null) {
  const { data } = await api.post("/api-keys", {
    name,
    daily_request_limit: dailyRequestLimit,
    expires_at: expiresAt,
  });
  return data;
}

export async function revokeApiKey(id) {
  await api.delete(`/api-keys/${id}`);
}
