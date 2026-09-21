import api from "./api";

export async function listScheduledTasks(workspaceId = null) {
  const params = workspaceId == null ? {} : { workspace_id: workspaceId };
  const { data } = await api.get("/scheduled-tasks", { params });
  return data;
}

export async function createScheduledTask(payload) {
  const { data } = await api.post("/scheduled-tasks", payload);
  return data;
}

export async function updateScheduledTask(id, payload) {
  const { data } = await api.patch(`/scheduled-tasks/${id}`, payload);
  return data;
}

export async function deleteScheduledTask(id) {
  await api.delete(`/scheduled-tasks/${id}`);
}

export async function runScheduledTask(id) {
  const { data } = await api.post(`/scheduled-tasks/${id}/run`);
  return data;
}

export async function listScheduledTaskRuns(id, limit = 20) {
  const { data } = await api.get(`/scheduled-tasks/${id}/runs`, { params: { limit } });
  return data;
}


export async function retryScheduledTaskRun(taskId, runId) {
  const { data } = await api.post(
    `/scheduled-tasks/${taskId}/runs/${runId}/retry`
  );
  return data;
}
