import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createScheduledTask,
  deleteScheduledTask,
  listScheduledTasks,
  updateScheduledTask,
  runScheduledTask,
  listScheduledTaskRuns,
} from "../lib/scheduledTasksApi";

function defaultLocalDateTime() {
  const date = new Date(Date.now() + 60 * 60 * 1000);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function formatRunAt(value) {
  return new Date(value).toLocaleString();
}

export default function ScheduledTasksPanel({
  workspaces = [],
  selectedWorkspaceId = null,
  onClose,
}) {
  const { t } = useTranslation();
  const [workspaceId, setWorkspaceId] = useState(selectedWorkspaceId);
  const [tasks, setTasks] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [scheduleType, setScheduleType] = useState("once");
  const [nextRunAt, setNextRunAt] = useState(defaultLocalDateTime);
  const [weekday, setWeekday] = useState("0");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [runsByTask, setRunsByTask] = useState({});
  const [expandedTaskId, setExpandedTaskId] = useState(null);
  const [runningTaskId, setRunningTaskId] = useState(null);

  const activeWorkspace = useMemo(
    () => workspaces.find((workspace) => workspace.id === Number(workspaceId)),
    [workspaces, workspaceId]
  );

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      setTasks(await listScheduledTasks(workspaceId));
    } catch {
      setError(t("scheduledTasks.loadError"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, [workspaceId]);

  const submit = async (event) => {
    event.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed || workspaceId == null) return;
    setSaving(true);
    setError("");
    try {
      await createScheduledTask({
        workspace_id: Number(workspaceId),
        prompt: trimmed,
        schedule_type: scheduleType,
        next_run_at: new Date(nextRunAt).toISOString(),
        weekday: scheduleType === "weekly" ? Number(weekday) : null,
      });
      setPrompt("");
      await refresh();
    } catch (err) {
      setError(err?.response?.data?.detail || t("scheduledTasks.saveError"));
    } finally {
      setSaving(false);
    }
  };

  const loadRuns = async (taskId) => {
    try {
      const runs = await listScheduledTaskRuns(taskId);
      setRunsByTask((prev) => ({ ...prev, [taskId]: runs }));
    } catch {
      setError(t("scheduledTasks.historyLoadError"));
    }
  };

  const toggleHistory = async (taskId) => {
    if (expandedTaskId === taskId) {
      setExpandedTaskId(null);
      return;
    }
    setExpandedTaskId(taskId);
    await loadRuns(taskId);
  };

  const runNow = async (task) => {
    setRunningTaskId(task.id);
    setError("");
    try {
      await runScheduledTask(task.id);
      await loadRuns(task.id);
      await refresh();
      setExpandedTaskId(task.id);
    } catch {
      setError(t("scheduledTasks.runNowError"));
    } finally {
      setRunningTaskId(null);
    }
  };

  const toggle = async (task) => {
    try {
      await updateScheduledTask(task.id, { is_active: !task.is_active });
      await refresh();
    } catch {
      setError(t("scheduledTasks.updateError"));
    }
  };

  const remove = async (task) => {
    if (!window.confirm(t("scheduledTasks.deleteConfirm"))) return;
    try {
      await deleteScheduledTask(task.id);
      await refresh();
    } catch {
      setError(t("scheduledTasks.deleteError"));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl border border-slate-200 bg-white p-5 shadow-xl dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">{t("scheduledTasks.title")}</h2>
            <p className="mt-1 text-sm text-slate-500">{t("scheduledTasks.description")}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg px-3 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">✕</button>
        </div>

        <div className="mt-4">
          <label className="block text-sm font-medium">
            {t("scheduledTasks.workspace")}
            <select
              value={workspaceId ?? ""}
              onChange={(event) => setWorkspaceId(event.target.value ? Number(event.target.value) : null)}
              className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-800"
            >
              {workspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
              ))}
            </select>
          </label>
        </div>

        <form onSubmit={submit} className="mt-4 rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
          <label className="block text-sm font-medium">
            {t("scheduledTasks.prompt")}
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              rows={3}
              maxLength={4000}
              placeholder={t("scheduledTasks.promptPlaceholder")}
              className="mt-1 w-full resize-y rounded-xl border border-slate-300 bg-white px-3 py-2 outline-none focus:ring-2 focus:ring-slate-300 dark:border-slate-700 dark:bg-slate-800"
            />
          </label>

          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <label className="text-sm font-medium">
              {t("scheduledTasks.frequency")}
              <select
                value={scheduleType}
                onChange={(event) => setScheduleType(event.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-800"
              >
                <option value="once">{t("scheduledTasks.once")}</option>
                <option value="daily">{t("scheduledTasks.daily")}</option>
                <option value="weekly">{t("scheduledTasks.weekly")}</option>
              </select>
            </label>

            <label className="text-sm font-medium">
              {t("scheduledTasks.nextRun")}
              <input
                type="datetime-local"
                value={nextRunAt}
                onChange={(event) => setNextRunAt(event.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-800"
              />
            </label>

            {scheduleType === "weekly" && (
              <label className="text-sm font-medium">
                {t("scheduledTasks.weekday")}
                <select
                  value={weekday}
                  onChange={(event) => setWeekday(event.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-800"
                >
                  {[0,1,2,3,4,5,6].map((day) => (
                    <option key={day} value={day}>{t(`scheduledTasks.day${day}`)}</option>
                  ))}
                </select>
              </label>
            )}
          </div>

          <button
            type="submit"
            disabled={saving || workspaceId == null || !prompt.trim()}
            className="mt-4 rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            {saving ? t("scheduledTasks.saving") : t("scheduledTasks.create")}
          </button>
        </form>

        {error && (
          <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="mt-5">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="font-semibold">{t("scheduledTasks.listTitle")}</h3>
            <button type="button" onClick={refresh} disabled={loading} className="text-sm text-slate-500 hover:text-slate-900">
              {t("scheduledTasks.refresh")}
            </button>
          </div>

          {loading ? (
            <p className="text-sm text-slate-500">{t("scheduledTasks.loading")}</p>
          ) : tasks.length === 0 ? (
            <p className="text-sm text-slate-500">{t("scheduledTasks.empty")}</p>
          ) : (
            <div className="space-y-2">
              {tasks.map((task) => (
                <div key={task.id}>
                  <div className="rounded-2xl border border-slate-200 p-3 dark:border-slate-700">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="whitespace-pre-wrap break-words text-sm font-medium">{task.prompt}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {t(`scheduledTasks.${task.schedule_type}`)} · {formatRunAt(task.next_run_at)}
                      </p>
                      {task.last_error && (
                        <p className="mt-1 text-xs text-red-600">{task.last_error}</p>
                      )}
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <button
                        type="button"
                        onClick={() => runNow(task)}
                        disabled={runningTaskId === task.id}
                        className="rounded-lg px-2 py-1 text-xs text-emerald-600 hover:bg-emerald-50 disabled:opacity-50 dark:hover:bg-emerald-900/20"
                      >
                        {runningTaskId === task.id ? t("scheduledTasks.running") : t("scheduledTasks.runNow")}
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleHistory(task.id)}
                        className="rounded-lg px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                      >
                        {expandedTaskId === task.id ? t("scheduledTasks.hideHistory") : t("scheduledTasks.history")}
                      </button>
                      <button
                        type="button"
                        onClick={() => toggle(task)}
                        className="rounded-lg px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                      >
                        {task.is_active ? t("scheduledTasks.pause") : t("scheduledTasks.resume")}
                      </button>
                      <button
                        type="button"
                        onClick={() => remove(task)}
                        className="rounded-lg px-2 py-1 text-xs text-red-600 hover:bg-red-100 dark:hover:bg-red-900/20"
                      >
                        {t("scheduledTasks.delete")}
                      </button>
                    </div>
                  </div>
                  {expandedTaskId === task.id && (
                  <div className="mt-3 space-y-2 rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
                    {(runsByTask[task.id] || []).length === 0 ? (
                      <p className="text-xs text-slate-500">{t("scheduledTasks.historyEmpty")}</p>
                    ) : (
                      runsByTask[task.id].map((run) => (
                        <div key={run.id} className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-white p-2 text-xs dark:border-slate-700 dark:bg-slate-900">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-medium">
                              {t(`scheduledTasks.status.${run.status}`)}
                            </span>
                            <span className="text-slate-400">{formatRunAt(run.created_at)}</span>
                          </div>
                          {run.finished_at ? (
                            <div className="text-slate-400">
                              {t("scheduledTasks.finishedAt", { date: formatRunAt(run.finished_at) })}
                            </div>
                          ) : null}
                          {run.error ? (
                            <div className="text-red-600">{run.error}</div>
                          ) : null}
                          {run.conversation_id ? (
                            <div className="text-slate-500">
                              {t("scheduledTasks.conversationCreated")}
                            </div>
                          ) : null}
                        </div>
                      ))
                    )}
                  </div>
                )}
                </div>
              ))}
            </div>
          )}
        </div>

        {activeWorkspace?.name && (
          <p className="mt-4 text-xs text-slate-400">{activeWorkspace.name}</p>
        )}
      </div>
    </div>
  );
}
