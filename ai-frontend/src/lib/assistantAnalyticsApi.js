import api from "./api";

export async function getAssistantAnalytics(assistantId, days = 30) {
  const { data } = await api.get(`/assistants/${assistantId}/analytics`, {
    params: { days },
  });
  return data;
}
