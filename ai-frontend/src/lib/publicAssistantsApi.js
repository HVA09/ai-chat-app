import api from "./api";

export async function getPublicAssistant(token) {
  const { data } = await api.get(`/public/assistants/${encodeURIComponent(token)}`);
  return data;
}

export async function duplicatePublicAssistant(token) {
  const { data } = await api.post(
    `/public/assistants/${encodeURIComponent(token)}/duplicate`
  );
  return data;
}
