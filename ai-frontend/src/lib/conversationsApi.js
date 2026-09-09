import api from "./api";

export async function listConversations() {
  const { data } = await api.get("/conversations");
  return data;
}

export async function getConversation(id) {
  const { data } = await api.get(`/conversations/${id}`);
  return data;
}

export async function renameConversation(id, title) {
  const { data } = await api.patch(`/conversations/${id}`, { title });
  return data;
}

export async function deleteConversation(id) {
  await api.delete(`/conversations/${id}`);
}
