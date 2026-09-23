import api from "./api";

export async function listSessions() {
  const { data } = await api.get("/auth/sessions");
  return data;
}

export async function revokeSession(id) {
  await api.delete(`/auth/sessions/${id}`);
}

export async function revokeAllSessions() {
  await api.post("/auth/sessions/revoke-all");
}
