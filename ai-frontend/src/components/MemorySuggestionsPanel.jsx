import { useTranslation } from "react-i18next";

export default function MemorySuggestionsPanel({
  suggestions,
  savingContent,
  onSave,
  onDismiss,
  onClose,
}) {
  const { t } = useTranslation();

  return (
    <section
      aria-labelledby="memory-suggestions-title"
      className="mb-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3
            id="memory-suggestions-title"
            className="text-sm font-semibold text-slate-900 dark:text-slate-100"
          >
            {t("memory.suggestTitle")}
          </h3>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-slate-500 dark:text-slate-400">
            {t("memory.suggestDescription")}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          {t("memory.suggestClose")}
        </button>
      </div>

      {suggestions.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
          {t("memory.suggestNoResults")}
        </p>
      ) : (
        <div className="mt-3 space-y-3">
          {suggestions.map((suggestion) => {
            const saving = savingContent === suggestion.content;
            return (
              <article
                key={suggestion.content}
                className="rounded-xl border border-slate-200 p-3 dark:border-slate-700"
              >
                <p className="text-sm font-medium leading-6 text-slate-800 dark:text-slate-100">
                  {suggestion.content}
                </p>
                <div className="mt-2 border-s-2 border-slate-200 ps-3 dark:border-slate-700">
                  <p className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    {t("memory.suggestEvidence")}
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-xs leading-5 text-slate-500 dark:text-slate-400">
                    “{suggestion.evidence}”
                  </p>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => onSave(suggestion)}
                    disabled={Boolean(savingContent)}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    {saving ? t("memory.suggestSaving") : t("memory.suggestSave")}
                  </button>
                  <button
                    type="button"
                    onClick={() => onDismiss(suggestion)}
                    disabled={Boolean(savingContent)}
                    className="rounded-lg px-3 py-1.5 text-xs text-slate-500 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:text-slate-300 dark:hover:bg-slate-800"
                  >
                    {t("memory.suggestDismiss")}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
