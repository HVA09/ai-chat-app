import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getAdminStats,
  getDailyAnalytics,
  downloadAnalyticsCsv,
  listAllUsers,
  updateUser,
  deleteUser,
  listAllConversations,
  adminDeleteConversation,
  listAuditLogs,
} from "../lib/adminApi";
import { getErrorMessage } from "../lib/errors";

const TAB_IDS = [
  { id: "stats", labelKey: "admin.tabStats" },
  { id: "users", labelKey: "admin.tabUsers" },
  { id: "conversations", labelKey: "admin.tabConversations" },
  { id: "logs", labelKey: "admin.tabLogs" },
];

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function StatsTab() {
  const { t } = useTranslation();
  const [stats, setStats] = useState(null);
  const [daily, setDaily] = useState([]);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    Promise.all([getAdminStats(), getDailyAnalytics(30)])
      .then(([statsData, dailyData]) => {
        setStats(statsData);
        setDaily(dailyData.map((p) => ({ ...p, dateLabel: p.date.slice(5) })));
      })
      .catch(() => setError(t("admin.statsError")));
  }, [t]);

  const handleExport = async () => {
    setExporting(true);
    try {
      await downloadAnalyticsCsv(30);
    } catch {
      setError(t("admin.exportError"));
    } finally {
      setExporting(false);
    }
  };

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!stats) return <p className="text-sm text-slate-400">...</p>;

  const cards = [
    [t("admin.statUsers"), stats.total_users],
    [t("admin.statConversations"), stats.total_conversations],
    [t("admin.statMessages"), stats.total_messages],
    [t("admin.statAIRequests"), stats.total_ai_requests],
    [t("admin.statFiles"), stats.total_files],
    [t("admin.statStorage"), formatSize(stats.storage_used_bytes)],
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {cards.map(([label, value]) => (
          <div key={label} className="rounded-2xl border border-slate-200 p-4 text-center">
            <p className="text-2xl font-semibold text-slate-900">{value}</p>
            <p className="mt-1 text-xs text-slate-500">{label}</p>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-900">{t("admin.last30Days")}</p>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs hover:bg-slate-50 disabled:opacity-50"
        >
          {exporting ? "..." : t("admin.exportCsv")}
        </button>
      </div>

      <div>
        <p className="mb-2 text-xs text-slate-500">{t("admin.newUsersChartLabel")}</p>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={daily}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="dateLabel" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="new_users" name={t("admin.chartUsers")} stroke="#0f172a" dot={false} />
            <Line
              type="monotone"
              dataKey="new_conversations"
              name={t("admin.chartConversations")}
              stroke="#64748b"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div>
        <p className="mb-2 text-xs text-slate-500">{t("admin.tokensChartLabel")}</p>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={daily}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="dateLabel" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="input_tokens" name={t("admin.inputTokens")} stroke="#0f172a" dot={false} />
            <Line
              type="monotone"
              dataKey="output_tokens"
              name={t("admin.outputTokens")}
              stroke="#64748b"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function UsersTab({ currentUserId }) {
  const { t } = useTranslation();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = () => {
    setLoading(true);
    listAllUsers()
      .then(setUsers)
      .catch(() => setError(t("admin.usersLoadError")))
      .finally(() => setLoading(false));
  };

  useEffect(refresh, []);

  const toggleActive = async (user) => {
    try {
      await updateUser(user.id, { is_active: !user.is_active });
      refresh();
    } catch {
      setError(t("admin.updateUserError"));
    }
  };

  const toggleRole = async (user) => {
    const nextRole = user.role === "admin" ? "user" : "admin";
    try {
      await updateUser(user.id, { role: nextRole });
      refresh();
    } catch {
      setError(t("admin.updateUserError"));
    }
  };

  const handleDelete = async (user) => {
    if (!window.confirm(t("admin.confirmDeleteUser", { email: user.email }))) return;
    try {
      await deleteUser(user.id);
      refresh();
    } catch (err) {
      setError(getErrorMessage(err, t("admin.usersLoadError")));
    }
  };

  if (loading) return <p className="text-sm text-slate-400">...</p>;

  return (
    <div className="space-y-2">
      {error && <p className="text-sm text-red-600">{error}</p>}
      {users.map((user) => (
        <div
          key={user.id}
          className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm"
        >
          <div className="min-w-0">
            <p className="truncate text-slate-900">{user.email}</p>
            <p className="text-xs text-slate-400">
              {user.role === "admin" ? t("admin.roleAdmin") : t("admin.roleUser")} ·{" "}
              {user.is_active ? t("admin.active") : t("admin.inactive")} ·{" "}
              {user.is_email_verified ? t("admin.emailVerified") : t("admin.emailNotVerified")}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <button
              onClick={() => toggleRole(user)}
              className="rounded-lg border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50"
            >
              {user.role === "admin" ? t("admin.removeAdmin") : t("admin.promoteAdmin")}
            </button>
            <button
              onClick={() => toggleActive(user)}
              className="rounded-lg border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50"
            >
              {user.is_active ? t("admin.deactivate") : t("admin.activate")}
            </button>
            {user.id !== currentUserId && (
              <button
                onClick={() => handleDelete(user)}
                className="rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50"
              >
                {t("admin.delete")}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function ConversationsTab() {
  const { t } = useTranslation();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = () => {
    setLoading(true);
    listAllConversations()
      .then(setConversations)
      .catch(() => setError(t("admin.conversationsLoadError")))
      .finally(() => setLoading(false));
  };

  useEffect(refresh, []);

  const handleDelete = async (conversation) => {
    if (!window.confirm(t("admin.confirmDeleteConversation", { title: conversation.title }))) return;
    try {
      await adminDeleteConversation(conversation.id);
      refresh();
    } catch {
      setError(t("admin.deleteConversationError"));
    }
  };

  if (loading) return <p className="text-sm text-slate-400">...</p>;
  if (conversations.length === 0) return <p className="text-sm text-slate-400">{t("admin.noConversations")}</p>;

  return (
    <div className="space-y-2">
      {error && <p className="text-sm text-red-600">{error}</p>}
      {conversations.map((conversation) => (
        <div
          key={conversation.id}
          className="flex items-center justify-between gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm"
        >
          <div className="min-w-0">
            <p className="truncate text-slate-900">{conversation.title}</p>
            <p className="text-xs text-slate-400">{conversation.user_email}</p>
          </div>
          <button
            onClick={() => handleDelete(conversation)}
            className="shrink-0 rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50"
          >
            {t("admin.delete")}
          </button>
        </div>
      ))}
    </div>
  );
}

function LogsTab() {
  const { t } = useTranslation();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listAuditLogs()
      .then(setLogs)
      .catch(() => setError(t("admin.logsLoadError")))
      .finally(() => setLoading(false));
  }, [t]);

  if (loading) return <p className="text-sm text-slate-400">...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (logs.length === 0) return <p className="text-sm text-slate-400">{t("admin.noLogs")}</p>;

  return (
    <div className="space-y-1.5">
      {logs.map((log) => (
        <div key={log.id} className="rounded-xl border border-slate-200 px-3 py-2 text-sm">
          <div className="flex items-center justify-between gap-2">
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              {log.event_type}
            </span>
            <span className="shrink-0 text-xs text-slate-400">
              {new Date(log.created_at).toLocaleString()}
            </span>
          </div>
          <p className="mt-1 text-slate-700">{log.description}</p>
        </div>
      ))}
    </div>
  );
}

export default function AdminDashboard({ currentUserId, onClose }) {
  const { t } = useTranslation();
  const [tab, setTab] = useState("stats");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="flex h-[85vh] w-full max-w-2xl flex-col rounded-3xl border border-slate-200 bg-white shadow-lg">
        <div className="flex items-center justify-between border-b border-slate-200 p-4">
          <h2 className="text-lg font-semibold text-slate-900">{t("admin.title")}</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

        <div className="flex gap-1 border-b border-slate-200 px-4 pt-2">
          {TAB_IDS.map((tabDef) => (
            <button
              key={tabDef.id}
              onClick={() => setTab(tabDef.id)}
              className={`rounded-t-xl px-3 py-2 text-sm ${
                tab === tabDef.id
                  ? "border-b-2 border-slate-900 font-medium text-slate-900"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              {t(tabDef.labelKey)}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {tab === "stats" && <StatsTab />}
          {tab === "users" && <UsersTab currentUserId={currentUserId} />}
          {tab === "conversations" && <ConversationsTab />}
          {tab === "logs" && <LogsTab />}
        </div>
      </div>
    </div>
  );
}
