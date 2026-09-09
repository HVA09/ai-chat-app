import api from "./api";

export async function getAdminStats() {
  const { data } = await api.get("/admin/stats");
  return data;
}

export async function getDailyAnalytics(days = 30) {
  const { data } = await api.get(`/admin/analytics/daily?days=${days}`);
  return data;
}

export async function downloadAnalyticsCsv(days = 30) {
  const response = await api.get(`/admin/analytics/export.csv?days=${days}`, {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = "analytics.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function listAllUsers() {
  const { data } = await api.get("/admin/users");
  return data;
}

export async function updateUser(id, fields) {
  const { data } = await api.patch(`/admin/users/${id}`, fields);
  return data;
}

export async function deleteUser(id) {
  await api.delete(`/admin/users/${id}`);
}

export async function listAllConversations() {
  const { data } = await api.get("/admin/conversations");
  return data;
}

export async function adminDeleteConversation(id) {
  await api.delete(`/admin/conversations/${id}`);
}

export async function listAuditLogs() {
  const { data } = await api.get("/admin/logs");
  return data;
}
