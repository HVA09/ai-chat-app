import api from "./api";

export async function getAssistantAnalytics(assistantId, days = 30) {
  const { data } = await api.get(`/assistants/${assistantId}/analytics`, {
    params: { days },
  });
  return data;
}

export async function getAssistantAnalyticsDaily(assistantId, days = 30) {
  const { data } = await api.get(`/assistants/${assistantId}/analytics/daily`, {
    params: { days },
  });
  return data;
}
