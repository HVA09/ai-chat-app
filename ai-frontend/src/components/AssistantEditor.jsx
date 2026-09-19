import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

export default function AssistantEditor({
  assistant = null,
  onSave,
  onClose,
  loading = false,
}) {
  const { t } = useTranslation();
  const [name, setName] = useState(assistant?.name || "");
  const [description, setDescription] = useState(assistant?.description || "");
  const [instructions, setInstructions] = useState(assistant?.instructions || "");

  useEffect(() => {
    setName(assistant?.name || "");
    setDescription(assistant?.description || "");
    setInstructions(assistant?.instructions || "");
  }, [assistant]);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!name.trim() || !instructions.trim()) return;
    onSave({
      name: name.trim(),
      description: description.trim() || null,
      instructions: instructions.trim(),
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-5 shadow-xl dark:border-slate-700 dark:bg-slate-900">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {assistant ? t("assistantEditor.editTitle") : t("assistantEditor.createTitle")}
            </h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              {t("assistantEditor.description")}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label={t("assistantEditor.close")}
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <label className="block">
            <span className="mb-1 block text-sm text-slate-600 dark:text-slate-300">
              {t("assistantEditor.name")}
            </span>
            <input
              autoFocus
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={100}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-800"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-sm text-slate-600 dark:text-slate-300">
              {t("assistantEditor.descriptionLabel")}
            </span>
            <input
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={300}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-800"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-sm text-slate-600 dark:text-slate-300">
              {t("assistantEditor.instructions")}
            </span>
            <textarea
              value={instructions}
              onChange={(event) => setInstructions(event.target.value)}
              maxLength={6000}
              rows={10}
              placeholder={t("assistantEditor.instructionsPlaceholder")}
              className="w-full resize-y rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-800"
            />
          </label>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              {t("assistantEditor.cancel")}
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim() || !instructions.trim()}
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {loading ? t("assistantEditor.saving") : t("assistantEditor.save")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
