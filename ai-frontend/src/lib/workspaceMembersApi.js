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
