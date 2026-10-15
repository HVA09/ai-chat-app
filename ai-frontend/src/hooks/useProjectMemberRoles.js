import { useEffect, useState } from "react";
import { listProjectMembers } from "../lib/projectMembersApi";

export default function useProjectMemberRoles({
  projects,
  selectedProjectId,
  selectedWorkspaceId,
  currentUserId,
  workspaces,
}) {
  const [projectMemberRoles, setProjectMemberRoles] = useState({});

  useEffect(() => {
    const project = projects.find(
      (item) => Number(item.id) === Number(selectedProjectId)
    );
    const workspaceRole = workspaces.find(
      (workspace) => workspace.id === selectedWorkspaceId
    )?.role;

    if (!project || currentUserId == null) return;

    if (
      Number(project.owner_id) === Number(currentUserId) ||
      ["owner", "admin"].includes(workspaceRole)
    ) {
      setProjectMemberRoles((current) => ({
        ...current,
        [project.id]: "manager",
      }));
      return;
    }

    let cancelled = false;
    listProjectMembers(project.id)
      .then((members) => {
        if (cancelled) return;
        const membership = members.find(
          (member) => Number(member.user_id) === Number(currentUserId)
        );
        setProjectMemberRoles((current) => ({
          ...current,
          [project.id]: membership?.role ?? null,
        }));
      })
      .catch(() => {
        if (!cancelled) {
          setProjectMemberRoles((current) => ({
            ...current,
            [project.id]: null,
          }));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [projects, selectedProjectId, selectedWorkspaceId, currentUserId, workspaces]);

  return projectMemberRoles;
}
