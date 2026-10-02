import api from "./api";

export async function listProjectMembers(projectId) {
  const { data } = await api.get(`/projects/${projectId}/members`);
  return data;
}

export async function addProjectMember(projectId, userId, role) {
  const { data } = await api.post(`/projects/${projectId}/members`, {
    user_id: Number(userId),
    role,
  });
  return data;
}

export async function updateProjectMember(projectId, memberId, role) {
  const { data } = await api.patch(
    `/projects/${projectId}/members/${memberId}`,
    { role }
  );
  return data;
}

export async function removeProjectMember(projectId, memberId) {
  await api.delete(`/projects/${projectId}/members/${memberId}`);
}
