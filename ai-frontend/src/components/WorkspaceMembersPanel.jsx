import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  inviteWorkspaceMember,
  listWorkspaceInvitations,
  listWorkspaceMembers,
  removeWorkspaceMember,
  revokeWorkspaceInvitation,
  updateWorkspaceMemberRole,
  listWorkspaceAuditLogs,
  getWorkspaceUsage,
} from "../lib/workspaceMembersApi";

export default function WorkspaceMembersPanel({ workspaceId, workspaceName, workspaceRole, onClose }) {
  const { t } = useTranslation();
  const [members, setMembers] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [usage, setUsage] = useState(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const manager = workspaceRole === "owner" || workspaceRole === "admin";
  const owner = workspaceRole === "owner";

  const load = async () => {
    setLoading(true);
    try {
      const [memberList, inviteList, auditList, usageData] = await Promise.all([
        listWorkspaceMembers(workspaceId),
        manager ? listWorkspaceInvitations(workspaceId) : Promise.resolve([]),
        manager ? listWorkspaceAuditLogs(workspaceId) : Promise.resolve([]),
        manager ? getWorkspaceUsage(workspaceId, 24).catch(() => null) : Promise.resolve(null),
      ]);
      setMembers(memberList);
      setInvitations(inviteList);
      setAuditLogs(auditList);
      setUsage(usageData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [workspaceId, workspaceRole]);

  const invite = async () => {
    if (!email.trim()) return;
    setBusy(true);
    try {
      await inviteWorkspaceMember(workspaceId, email.trim(), role);
      setEmail("");
      await load();
    } catch {
      // App-level auth/API errors are handled globally; local failure leaves the form intact.
    } finally {
      setBusy(false);
    }
  };

  const updateRole = async (member, nextRole) => {
    setBusy(true);
    try {
      await updateWorkspaceMemberRole(workspaceId, member.id, nextRole);
      await load();
    } finally {
      setBusy(false);
    }
  };

  const remove = async (member) => {
    if (!window.confirm(t("workspaceMembers.confirmRemove", { email: member.email }))) return;
    setBusy(true);
    try {
      await removeWorkspaceMember(workspaceId, member.id);
      await load();
    } finally {
      setBusy(false);
    }
  };

  const revoke = async (invitation) => {
    setBusy(true);
    try {
      await revokeWorkspaceInvitation(workspaceId, invitation.id);
      await load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl bg-white p-5 shadow-xl dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">{t("workspaceMembers.title")}</h2>
            <p className="text-sm text-slate-500">{workspaceName}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg px-3 py-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">✕</button>
        </div>

        {manager && (
          <div className="mt-5 rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
            <h3 className="font-medium">{t("workspaceMembers.inviteTitle")}</h3>
            <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_auto_auto]">
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                type="email"
                placeholder={t("workspaceMembers.emailPlaceholder")}
                className="rounded-xl border border-slate-200 px-3 py-2 dark:border-slate-700 dark:bg-slate-800"
              />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="rounded-xl border border-slate-200 px-3 py-2 dark:border-slate-700 dark:bg-slate-800"
              >
                <option value="member">{t("workspaceMembers.memberRole")}</option>
                {owner && <option value="admin">{t("workspaceMembers.adminRole")}</option>}
              </select>
              <button
                type="button"
                disabled={busy}
                onClick={invite}
                className="rounded-xl bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
              >
                {t("workspaceMembers.invite")}
              </button>
            </div>
            <p className="mt-2 text-xs text-slate-400">{t("workspaceMembers.existingUserOnly")}</p>
          </div>
        )}

        <div className="mt-5">
          <h3 className="font-medium">{t("workspaceMembers.membersTitle")}</h3>
          {loading ? (
            <p className="mt-3 text-sm text-slate-400">...</p>
          ) : (
            <div className="mt-3 space-y-2">
              {members.map((member) => {
                const canManage =
                  owner
                    ? member.role !== "owner"
                    : workspaceRole === "admin" && member.role === "member";
                return (
                  <div key={member.id} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 p-3 dark:border-slate-700">
                    <div className="min-w-0">
                      <div className="truncate font-medium">{member.full_name || member.email}</div>
                      <div className="truncate text-xs text-slate-500">{member.email}</div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {owner && member.role !== "owner" ? (
                        <select
                          value={member.role}
                          disabled={busy}
                          onChange={(e) => updateRole(member, e.target.value)}
                          className="rounded-lg border border-slate-200 px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-800"
                        >
                          <option value="member">{t("workspaceMembers.memberRole")}</option>
                          <option value="admin">{t("workspaceMembers.adminRole")}</option>
                        </select>
                      ) : (
                        <span className="rounded-full bg-slate-100 px-2 py-1 text-xs dark:bg-slate-800">{member.role}</span>
                      )}
                      {canManage && (
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => remove(member)}
                          className="rounded-lg px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                        >
                          {t("workspaceMembers.remove")}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
              {members.length === 0 && <p className="text-sm text-slate-400">{t("workspaceMembers.noMembers")}</p>}
            </div>
          )}
        </div>

        {manager && (
          <div className="mt-5">
            <h3 className="font-medium">{t("workspaceMembers.pendingTitle")}</h3>
            <div className="mt-3 space-y-2">
              {invitations.map((invitation) => (
                <div key={invitation.id} className="flex items-center justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-3 dark:border-amber-900/40 dark:bg-amber-950/20">
                  <div className="min-w-0">
                    <div className="truncate font-medium">{invitation.email}</div>
                    <div className="text-xs text-slate-500">{invitation.role} · {new Date(invitation.expires_at).toLocaleDateString()}</div>
                  </div>
                  <button type="button" disabled={busy} onClick={() => revoke(invitation)} className="rounded-lg px-2 py-1 text-xs text-red-600 hover:bg-red-100 disabled:opacity-50">
                    {t("workspaceMembers.revoke")}
                  </button>
                </div>
              ))}
              {invitations.length === 0 && <p className="text-sm text-slate-400">{t("workspaceMembers.noPending")}</p>}
            </div>
          </div>
        )}

        {manager && usage && (
          <div className="mt-5 rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-medium">{t("workspaceUsage.title")}</h3>
              <span className="text-xs text-slate-400">{t("workspaceUsage.window", { hours: usage.window_hours })}</span>
            </div>

            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800">
                <div className="text-xs text-slate-500">{t("workspaceUsage.requests")}</div>
                <div className="mt-1 text-lg font-semibold">{usage.used_requests}</div>
              </div>
              <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800">
                <div className="text-xs text-slate-500">{t("workspaceUsage.inputTokens")}</div>
                <div className="mt-1 text-lg font-semibold">{usage.input_tokens}</div>
              </div>
              <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800">
                <div className="text-xs text-slate-500">{t("workspaceUsage.outputTokens")}</div>
                <div className="mt-1 text-lg font-semibold">{usage.output_tokens}</div>
              </div>
            </div>

            <div className="mt-4">
              <div className="mb-2 flex items-center justify-between gap-2">
                <h4 className="text-sm font-medium">{t("workspaceUsage.byMember")}</h4>
                <span className="text-xs text-slate-400">
                  {t("workspaceUsage.totalTokens")}: {usage.total_tokens}
                </span>
              </div>
              {usage.members.length === 0 ? (
                <p className="text-sm text-slate-400">{t("workspaceUsage.noData")}</p>
              ) : (
                <div className="space-y-2">
                  {usage.members.map((member) => (
                    <div key={member.user_id} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-medium">{member.full_name || member.email}</div>
                          <div className="truncate text-xs text-slate-400">{member.email}</div>
                        </div>
                        <div className="text-xs text-slate-500">
                          {member.used_requests} {t("workspaceUsage.requestsShort")}
                        </div>
                      </div>
                      <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-500">
                        <span>{t("workspaceUsage.inputShort")}: {member.input_tokens}</span>
                        <span>{t("workspaceUsage.outputShort")}: {member.output_tokens}</span>
                        <span>{t("workspaceUsage.totalShort")}: {member.total_tokens}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {manager && (
          <div className="mt-5">
            <h3 className="font-medium">{t("workspaceMembers.activityTitle")}</h3>
            <div className="mt-3 space-y-2">
              {auditLogs.map((log) => (
                <div key={log.id} className="rounded-2xl border border-slate-200 p-3 dark:border-slate-700">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">{log.event_type}</span>
                    <span className="text-xs text-slate-400">{new Date(log.created_at).toLocaleString()}</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">{log.description}</p>
                  {log.actor_email && <p className="mt-1 text-xs text-slate-400">{log.actor_email}</p>}
                </div>
              ))}
              {auditLogs.length === 0 && (
                <p className="text-sm text-slate-400">{t("workspaceMembers.noActivity")}</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
