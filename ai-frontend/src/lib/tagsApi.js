import api from "./api";

export async function listTags() {
  const { data } = await api.get("/tags");
  return data;
}

export async function createTag(name, color = "#64748B") {
  const { data } = await api.post("/tags", { name, color });
  return data;
}

export async function updateTag(id, name, color) {
  const { data } = await api.patch(`/tags/${id}`, { name, color });
  return data;
}

export async function deleteTag(id) {
  await api.delete(`/tags/${id}`);
}

export async function setConversationTags(conversationId, tagIds) {
  const { data } = await api.put(`/conversations/${conversationId}/tags`, {
    tag_ids: tagIds,
  });
  return data;
}
