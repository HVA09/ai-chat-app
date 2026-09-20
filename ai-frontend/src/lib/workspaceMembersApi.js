import api from "./api";

export async function listWorkspaceMembers(workspaceId) {
  const { data } = await api.get(`/workspaces/${workspaceId}/members`);
  return data;
}

export async function inviteWorkspaceMember(workspaceId, email, role) {
  const { data } = await api.post(`/workspaces/${workspaceId}/invitations`, { email, role });
  return data;
}

export async function listWorkspaceInvitations(workspaceId) {
  const { data } = await api.get(`/workspaces/${workspaceId}/invitations`);
  return data;
}

export async function revokeWorkspaceInvitation(workspaceId, invitationId) {
  await api.delete(`/workspaces/${workspaceId}/invitations/${invitationId}`);
}

export async function updateWorkspaceMemberRole(workspaceId, memberId, role) {
  const { data } = await api.patch(`/workspaces/${workspaceId}/members/${memberId}/role`, { role });
  return data;
}

export async function removeWorkspaceMember(workspaceId, memberId) {
  await api.delete(`/workspaces/${workspaceId}/members/${memberId}`);
}

export async function acceptWorkspaceInvitation(token) {
  const { data } = await api.post("/workspace-invitations/accept", { token });
  return data;
}

export async function listWorkspaceAuditLogs(workspaceId) {
  const { data } = await api.get(`/workspaces/${workspaceId}/audit-logs`);
  return data;
}


export async function getWorkspaceUsage(workspaceId, windowHours = 24) {
  const { data } = await api.get(`/workspaces/${workspaceId}/usage`, {
    params: { window_hours: windowHours },
  });
  return data;
}


export async function downloadWorkspaceUsageCsv(workspaceId, windowHours = 24) {
  const response = await api.get(`/workspaces/${workspaceId}/usage.csv`, {
    params: { window_hours: windowHours },
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = `workspace-${workspaceId}-usage-${windowHours}h.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
