import api from "./api";

export async function listNotifications() {
  const { data } = await api.get("/notifications");
  return data;
}

export async function markNotificationRead(id) {
  const { data } = await api.post(`/notifications/${id}/read`);
  return data;
}

export async function markAllNotificationsRead() {
  const { data } = await api.post("/notifications/read-all");
  return data;
}

export function buildNotificationsWebSocketUrl() {
  const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const wsBase = baseURL.replace(/^http/, "ws");
  return `${wsBase}/ws/notifications`;
}
