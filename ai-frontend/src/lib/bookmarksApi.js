import api from "./api";

export async function listBookmarkedMessages() {
  const { data } = await api.get("/conversations/bookmarks");
  return data;
}

export async function toggleMessageBookmark(conversationId, messageIndex) {
  const { data } = await api.patch(
    `/chat/${conversationId}/messages/${messageIndex}/bookmark`
  );
  return data;
}
