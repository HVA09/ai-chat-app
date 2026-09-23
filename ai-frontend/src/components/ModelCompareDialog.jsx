import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { compareChatModels } from "../lib/chatApi";

export default function ModelCompareDialog({
  models = [],
  initialPrompt = "",
  conversationId = null,
  workspaceId = null,
  projectId = null,
  assistantId = null,
  onClose,
}) {
  const { t } = useTranslation();
  const [prompt, setPrompt] = useState(initialPrompt);
  const [modelA, setModelA] = useState(models[0]?.id || "");
  const [modelB, setModelB] = useState(models[1]?.id || models[0]?.id || "");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!modelA && models[0]) setModelA(models[0].id);
    if (!modelB && models[1]) setModelB(models[1].id);
  }, [modelA, modelB, models]);

  const canCompare = useMemo(
    () => models.length >= 2 && prompt.trim() && modelA && modelB && modelA !== modelB && !loading,
    [models.length, prompt, modelA, modelB, loading]
  );

  const runComparison = async () => {
    if (!canCompare) return;
    setLoading(true);
    setError("");
    setResults([]);
    try {
      const data = await compareChatModels({
        message: prompt.trim(),
        conversation_id: conversationId,
        workspace_id: workspaceId,
        project_id: projectId,
        assistant_id: assistantId,
        model_a: modelA,
        model_b: modelB,
      });
      setResults(data.results || []);
    } catch (err) {
      setError(err?.response?.data?.detail || t("modelCompare.error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-3">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="model-compare-title"
        className="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-3xl border border-slate-200 bg-white p-4 shadow-2xl dark:border-slate-700 dark:bg-slate-900"
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 id="model-compare-title" className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {t("modelCompare.title")}
            </h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t("modelCompare.hint")}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl px-3 py-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            ✕
          </button>
        </div>

        {models.length < 2 ? (
          <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
            {t("modelCompare.needTwoModels")}
          </div>
        ) : (
          <>
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              maxLength={4000}
              rows={5}
              placeholder={t("modelCompare.promptPlaceholder")}
              className="mt-4 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />

            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <label className="text-sm text-slate-600 dark:text-slate-300">
                {t("modelCompare.modelA")}
                <select
                  value={modelA}
                  onChange={(event) => setModelA(event.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                >
                  {models.map((model) => (
                    <option key={model.id} value={model.id}>{model.label}</option>
                  ))}
                </select>
              </label>

              <label className="text-sm text-slate-600 dark:text-slate-300">
                {t("modelCompare.modelB")}
                <select
                  value={modelB}
                  onChange={(event) => setModelB(event.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                >
                  {models.map((model) => (
                    <option key={model.id} value={model.id}>{model.label}</option>
                  ))}
                </select>
              </label>
            </div>

            {error ? (
              <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
                {error}
              </div>
            ) : null}

            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                {t("modelCompare.cancel")}
              </button>
              <button
                type="button"
                onClick={runComparison}
                disabled={!canCompare}
                className="rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
              >
                {loading ? t("modelCompare.running") : t("modelCompare.compare")}
              </button>
            </div>

            {results.length > 0 && (
              <div className="mt-5 grid gap-3 md:grid-cols-2">
                {results.map((result) => (
                  <article key={result.model} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="font-semibold text-slate-900 dark:text-slate-100">{result.model}</h3>
                      <span className="text-xs text-slate-400">{result.latency_ms}ms</span>
                    </div>
                    <div className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700 dark:text-slate-200">
                      {result.text}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
