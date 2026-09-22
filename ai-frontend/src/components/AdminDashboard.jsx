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
  getModelUsage,
  getProviderUsage,
  getProviderLatency,
  getCostUsage,
  getCostBudget,
  getFeedbackAnalytics,
  downloadAnalyticsCsv,
  listAllUsers,
  updateUser,
  deleteUser,
  listAllConversations,
  adminDeleteConversation,
  listAuditLogs,
  listPlans,
  updatePlan,
} from "../lib/adminApi";
import { getErrorMessage } from "../lib/errors";

const TAB_IDS = [
  { id: "stats", labelKey: "admin.tabStats" },
  { id: "plans", labelKey: "admin.tabPlans" },
  { id: "users", labelKey: "admin.tabUsers" },
  { id: "conversations", labelKey: "admin.tabConversations" },
  { id: "logs", labelKey: "admin.tabLogs" },
];

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const ANALYTICS_RANGES = [7, 30, 90, 365];

function StatsTab() {
  const { t } = useTranslation();
  const [stats, setStats] = useState(null);
  const [daily, setDaily] = useState([]);
  const [feedback, setFeedback] = useState(null);
  const [modelUsage, setModelUsage] = useState([]);
  const [providerUsage, setProviderUsage] = useState([]);
  const [providerLatency, setProviderLatency] = useState([]);
  const [costUsage, setCostUsage] = useState([]);
  const [costBudget, setCostBudget] = useState(null);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);
  const [analyticsDays, setAnalyticsDays] = useState(30);

  useEffect(() => {
    Promise.all([
      getAdminStats(),
      getDailyAnalytics(analyticsDays),
      getModelUsage(analyticsDays),
      getProviderUsage(analyticsDays),
      getProviderLatency(analyticsDays),
      getCostUsage(analyticsDays),
      getCostBudget(),
      getFeedbackAnalytics(analyticsDays),
    ])
.then(([statsData, dailyData, modelUsageData, providerUsageData, providerLatencyData, costUsageData, costBudgetData, feedbackData]) => {
        setStats(statsData);
        setDaily(dailyData.map((p) => ({ ...p, dateLabel: p.date.slice(5) })));
        setModelUsage(modelUsageData);
        setProviderUsage(providerUsageData);
        setProviderLatency(providerLatencyData);
        setCostUsage(costUsageData);
        setCostBudget(costBudgetData);
        setFeedback(feedbackData);
      })
      .catch(() => setError(t("admin.statsError")));
  }, [t, analyticsDays]);

  const handleExport = async () => {
    setExporting(true);
    try {
      await downloadAnalyticsCsv(analyticsDays);
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
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-slate-200 p-3">
        <div>
          <p className="text-sm font-medium text-slate-900">{t("admin.analyticsRangeTitle")}</p>
          <p className="text-xs text-slate-500">{t("admin.analyticsRangeHint")}</p>
        </div>
        <div className="flex flex-wrap gap-1 rounded-xl bg-slate-100 p-1">
          {ANALYTICS_RANGES.map((days) => (
            <button
              key={days}
              type="button"
              onClick={() => setAnalyticsDays(days)}
              aria-pressed={analyticsDays === days}
              className={`rounded-lg px-3 py-1.5 text-xs transition ${
                analyticsDays === days
                  ? "bg-slate-900 font-medium text-white shadow-sm"
                  : "text-slate-600 hover:bg-white hover:text-slate-900"
              }`}
            >
              {t("admin.analyticsDays", { days })}
            </button>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {cards.map(([label, value]) => (
          <div key={label} className="rounded-2xl border border-slate-200 p-4 text-center">
            <p className="text-2xl font-semibold text-slate-900">{value}</p>
            <p className="mt-1 text-xs text-slate-500">{label}</p>
          </div>
        ))}
      </div>

      {modelUsage.length > 0 && (
        <div className="rounded-2xl border border-slate-200 p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-900">{t("admin.modelUsageTitle")}</p>
            <span className="text-xs text-slate-400">{t("admin.lastNDays", { days: analyticsDays })}</span>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead className="border-b border-slate-200 text-xs text-slate-500">
                <tr>
                  <th className="px-2 py-2 font-medium">{t("admin.modelColumn")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.modelRequests")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.modelInputTokens")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.modelOutputTokens")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.modelTotalTokens")}</th>
                </tr>
              </thead>
              <tbody>
                {modelUsage.map((item) => (
                  <tr key={item.model} className="border-b border-slate-100 last:border-0">
                    <td className="px-2 py-2 font-medium text-slate-900">{item.model}</td>
                    <td className="px-2 py-2 text-right text-slate-600">{item.requests}</td>
                    <td className="px-2 py-2 text-right text-slate-600">{item.input_tokens}</td>
                    <td className="px-2 py-2 text-right text-slate-600">{item.output_tokens}</td>
                    <td className="px-2 py-2 text-right font-medium text-slate-900">{item.total_tokens}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {providerUsage.length > 0 && (
        <div className="rounded-2xl border border-slate-200 p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-900">{t("admin.providerUsageTitle")}</p>
            <span className="text-xs text-slate-400">{t("admin.lastNDays", { days: analyticsDays })}</span>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead className="border-b border-slate-200 text-xs text-slate-500">
                <tr>
                  <th className="px-2 py-2 font-medium">{t("admin.providerColumn")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.providerRequests")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.providerInputTokens")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.providerOutputTokens")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.providerTotalTokens")}</th>
                </tr>
              </thead>
              <tbody>
                {providerUsage.map((item) => (
                  <tr key={item.provider} className="border-b border-slate-100 last:border-0">
                    <td className="px-2 py-2 font-medium text-slate-900">{item.provider}</td>
                    <td className="px-2 py-2 text-right text-slate-600">{item.requests}</td>
                    <td className="px-2 py-2 text-right text-slate-600">{item.input_tokens}</td>
                    <td className="px-2 py-2 text-right text-slate-600">{item.output_tokens}</td>
                    <td className="px-2 py-2 text-right font-medium text-slate-900">{item.total_tokens}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {providerLatency.length > 0 && (
        <div className="rounded-2xl border border-slate-200 p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-900">{t("admin.providerLatencyTitle")}</p>
            <span className="text-xs text-slate-400">{t("admin.lastNDays", { days: analyticsDays })}</span>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead className="border-b border-slate-200 text-xs text-slate-500">
                <tr>
                  <th className="px-2 py-2 font-medium">{t("admin.providerColumn")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.providerRequests")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.avgLatency")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.minLatency")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.maxLatency")}</th>
                </tr>
              </thead>
              <tbody>
                {providerLatency.map((item) => (
                  <tr key={item.provider} className="border-b border-slate-100 last:border-0">
                    <td className="px-2 py-2 font-medium text-slate-900">{item.provider}</td>
                    <td className="px-2 py-2 text-right text-slate-600">{item.requests}</td>
                    <td className="px-2 py-2 text-right text-slate-600">{item.avg_latency_ms} ms</td>
                    <td className="px-2 py-2 text-right text-slate-600">{item.min_latency_ms} ms</td>
                    <td className="px-2 py-2 text-right font-medium text-slate-900">{item.max_latency_ms} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}



      {costUsage.length > 0 && (
        <div className="rounded-2xl border border-slate-200 p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-900">{t("admin.costUsageTitle")}</p>
            <span className="text-xs text-slate-400">{t("admin.lastNDays", { days: analyticsDays })}</span>
          </div>
          <p className="mt-1 text-xs text-slate-400">{t("admin.costUsageHint")}</p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="border-b border-slate-200 text-xs text-slate-500">
                <tr>
                  <th className="px-2 py-2 font-medium">{t("admin.providerColumn")}</th>
                  <th className="px-2 py-2 font-medium">{t("admin.modelColumn")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.costRequests")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.costInput")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.costOutput")}</th>
                  <th className="px-2 py-2 text-right font-medium">{t("admin.costTotal")}</th>
                </tr>
              </thead>
              <tbody>
                {costUsage.map((item) => (
                  <tr key={`${item.provider}:${item.model}`} className="border-b border-slate-100 last:border-0">
                    <td className="px-2 py-2 font-medium text-slate-900">{item.provider}</td>
                    <td className="px-2 py-2 text-slate-700">{item.model}</td>
                    <td className="px-2 py-2 text-right text-slate-600">{item.requests}</td>
                    <td className="px-2 py-2 text-right text-slate-600">
                      {item.input_cost_usd === null ? "—" : `${item.input_cost_usd.toFixed(6)}`}
                    </td>
                    <td className="px-2 py-2 text-right text-slate-600">
                      {item.output_cost_usd === null ? "—" : `${item.output_cost_usd.toFixed(6)}`}
                    </td>
                    <td className="px-2 py-2 text-right font-medium text-slate-900">
                      {item.total_cost_usd === null ? "—" : `${item.total_cost_usd.toFixed(6)}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {costBudget && (
        <div className="rounded-2xl border border-slate-200 p-4">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-medium text-slate-900">{t("admin.costBudgetTitle")}</p>
            <span className="text-xs text-slate-400">{t("admin.costBudgetMonth", { month: costBudget.month_start })}</span>
          </div>

          {costBudget.budget_usd === null ? (
            <p className="mt-3 text-sm text-slate-500">{t("admin.costBudgetDisabled")}</p>
          ) : (
            <>
              <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                <div className="rounded-xl bg-slate-50 p-3">
                  <p className="text-lg font-semibold text-slate-900">
                    ${costBudget.spent_usd.toFixed(4)}
                  </p>
                  <p className="text-xs text-slate-500">{t("admin.costBudgetSpent")}</p>
                </div>
                <div className="rounded-xl bg-slate-50 p-3">
                  <p className="text-lg font-semibold text-slate-900">
                    ${costBudget.budget_usd.toFixed(2)}
                  </p>
                  <p className="text-xs text-slate-500">{t("admin.costBudgetLimit")}</p>
                </div>
                <div className="rounded-xl bg-slate-50 p-3">
                  <p className="text-lg font-semibold text-slate-900">
                    ${costBudget.remaining_usd.toFixed(4)}
                  </p>
                  <p className="text-xs text-slate-500">{t("admin.costBudgetRemaining")}</p>
                </div>
              </div>

              <div className="mt-3">
                <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
                  <span>{t("admin.costBudgetUsage")}</span>
                  <span>{costBudget.usage_percent.toFixed(1)}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-slate-900"
                    style={{ width: `${Math.min(costBudget.usage_percent, 100)}%` }}
                  />
                </div>
              </div>

              {costBudget.over_budget && (
                <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {t("admin.costBudgetExceeded")}
                </p>
              )}
              {costBudget.unpriced_requests > 0 && (
                <p className="mt-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
                  {t("admin.costBudgetUnpriced", { count: costBudget.unpriced_requests })}
                </p>
              )}
            </>
          )}
        </div>
      )}

      {feedback && (
        <div className="rounded-2xl border border-slate-200 p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-900">{t("admin.feedbackTitle")}</p>
            <span className="text-xs text-slate-400">{t("admin.lastNDays", { days: analyticsDays })}</span>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-xl bg-slate-50 p-3 text-center">
              <p className="text-lg font-semibold text-slate-900">{feedback.total_rated}</p>
              <p className="text-xs text-slate-500">{t("admin.feedbackRated")}</p>
            </div>
            <div className="rounded-xl bg-emerald-50 p-3 text-center">
              <p className="text-lg font-semibold text-emerald-700">{feedback.positive}</p>
              <p className="text-xs text-emerald-700">{t("admin.feedbackPositive")}</p>
            </div>
            <div className="rounded-xl bg-red-50 p-3 text-center">
              <p className="text-lg font-semibold text-red-700">{feedback.negative}</p>
              <p className="text-xs text-red-700">{t("admin.feedbackNegative")}</p>
            </div>
            <div className="rounded-xl bg-blue-50 p-3 text-center">
              <p className="text-lg font-semibold text-blue-700">
                {feedback.positive_rate === null ? "—" : String(feedback.positive_rate) + "%"}
              </p>
              <p className="text-xs text-blue-700">{t("admin.feedbackPositiveRate")}</p>
            </div>
          </div>
        </div>
      )}

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
        <p className="mb-2 text-xs text-slate-500">{t("admin.newUsersChartLabel")} · {t("admin.lastNDays", { days: analyticsDays })}</p>
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
        <p className="mb-2 text-xs text-slate-500">{t("admin.tokensChartLabel")} · {t("admin.lastNDays", { days: analyticsDays })}</p>
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

function PlansTab() {
  const { t } = useTranslation();
  const [plans, setPlans] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [error, setError] = useState("");
  const [savedId, setSavedId] = useState(null);

  const refresh = () => {
    setLoading(true);
    listPlans()
      .then((items) => {
        setPlans(items);
        setDrafts(
          Object.fromEntries(
            items.map((plan) => [
              plan.id,
              {
                daily_ai_request_limit: String(plan.daily_ai_request_limit),
                allowed_models: (plan.allowed_models || []).join(", "),
                is_active: Boolean(plan.is_active),
              },
            ])
          )
        );
      })
      .catch((err) => setError(getErrorMessage(err, t("admin.plansLoadError"))))
      .finally(() => setLoading(false));
  };

  useEffect(refresh, []);

  const updateDraft = (id, patch) => {
    setDrafts((previous) => ({
      ...previous,
      [id]: { ...previous[id], ...patch },
    }));
  };

  const save = async (plan) => {
    const draft = drafts[plan.id];
    setSavingId(plan.id);
    setSavedId(null);
    setError("");
    try {
      const allowed_models = draft.allowed_models
        .split(",")
        .map((model) => model.trim())
        .filter(Boolean);
      const updated = await updatePlan(plan.id, {
        daily_ai_request_limit: Number(draft.daily_ai_request_limit),
        allowed_models,
        is_active: draft.is_active,
      });
      setPlans((previous) => previous.map((item) => (item.id === plan.id ? updated : item)));
      setDrafts((previous) => ({
        ...previous,
        [plan.id]: {
          daily_ai_request_limit: String(updated.daily_ai_request_limit),
          allowed_models: (updated.allowed_models || []).join(", "),
          is_active: Boolean(updated.is_active),
        },
      }));
      setSavedId(plan.id);
    } catch (err) {
      setError(getErrorMessage(err, t("admin.planSaveError")));
    } finally {
      setSavingId(null);
    }
  };

  if (loading) return <p className="text-sm text-slate-400">...</p>;
  if (error && plans.length === 0) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <div className="space-y-3">
      {error && <p className="text-sm text-red-600">{error}</p>}
      {plans.map((plan) => {
        const draft = drafts[plan.id];
        return (
          <div key={plan.id} className="rounded-2xl border border-slate-200 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="font-semibold text-slate-900">{plan.name}</p>
                <p className="text-xs text-slate-400">
                  {plan.price_cents / 100} {plan.currency.toUpperCase()} / {plan.interval}
                </p>
              </div>
              <label className="flex items-center gap-2 text-xs text-slate-600">
                <input
                  type="checkbox"
                  checked={draft.is_active}
                  onChange={(event) => updateDraft(plan.id, { is_active: event.target.checked })}
                />
                {t("admin.planActive")}
              </label>
            </div>

            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-slate-500">
                  {t("admin.planDailyLimit")}
                </span>
                <input
                  type="number"
                  min="1"
                  value={draft.daily_ai_request_limit}
                  onChange={(event) =>
                    updateDraft(plan.id, { daily_ai_request_limit: event.target.value })
                  }
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-slate-300"
                />
              </label>

              <label className="block">
                <span className="mb-1 block text-xs font-medium text-slate-500">
                  {t("admin.planModels")}
                </span>
                <input
                  type="text"
                  value={draft.allowed_models}
                  onChange={(event) =>
                    updateDraft(plan.id, { allowed_models: event.target.value })
                  }
                  placeholder='gemini-2.5-flash, gemini-2.5-pro or *'
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-slate-300"
                />
              </label>
            </div>

            <div className="mt-3 flex items-center justify-between">
              <p className="text-xs text-slate-400">{t("admin.planModelsHint")}</p>
              <button
                type="button"
                onClick={() => save(plan)}
                disabled={savingId === plan.id}
                className="rounded-xl bg-slate-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
              >
                {savingId === plan.id
                  ? "..."
                  : savedId === plan.id
                    ? t("admin.planSaved")
                    : t("admin.planSave")}
              </button>
            </div>
          </div>
        );
      })}
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
          {tab === "plans" && <PlansTab />}
          {tab === "users" && <UsersTab currentUserId={currentUserId} />}
          {tab === "conversations" && <ConversationsTab />}
          {tab === "logs" && <LogsTab />}
        </div>
      </div>
    </div>
  );
}
