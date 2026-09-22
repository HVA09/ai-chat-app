import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

export default function ProjectEditor({ project = null, onClose, onSave }) {
  const { t } = useTranslation();
  const isEditing = Boolean(project);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [validationError, setValidationError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setName(project?.name ?? "");
    setDescription(project?.description ?? "");
    setInstructions(project?.instructions ?? "");
    setValidationError("");
  }, [project]);

  const submit = async (event) => {
    event.preventDefault();
    const normalizedName = name.trim();
    const normalizedDescription = description.trim();
    const normalizedInstructions = instructions.trim();

    if (!normalizedName) {
      setValidationError(t("projectEditor.requiredError"));
      return;
    }

    setValidationError("");
    setSaving(true);
    try {
      await onSave({
        name: normalizedName,
        description: normalizedDescription || null,
        instructions: normalizedInstructions || null,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="project-editor-title"
    >
      <form
        onSubmit={submit}
        className="w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-slate-700 dark:bg-slate-900"
      >
        <div className="mb-5 flex items-center justify-between gap-4">
          <div>
            <h2 id="project-editor-title" className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {isEditing ? t("projectEditor.editTitle") : t("projectEditor.createTitle")}
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {t("projectEditor.subtitle")}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            aria-label={t("projectEditor.close")}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50 dark:hover:bg-slate-800"
          >
            ✕
          </button>
        </div>

        <div className="space-y-4">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
              {t("projectEditor.nameLabel")}
            </span>
            <input
              autoFocus
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={120}
              placeholder={t("projectEditor.namePlaceholder")}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
              {t("projectEditor.descriptionLabel")}
            </span>
            <input
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={1000}
              placeholder={t("projectEditor.descriptionPlaceholder")}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
              {t("projectEditor.instructionsLabel")}
            </span>
            <textarea
              value={instructions}
              onChange={(event) => setInstructions(event.target.value)}
              maxLength={6000}
              rows={10}
              placeholder={t("projectEditor.instructionsPlaceholder")}
              className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
            />
            <span className="mt-1 block text-end text-xs text-slate-400">
              {instructions.length}/6000
            </span>
          </label>

          {validationError && (
            <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {validationError}
            </div>
          )}
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            {t("projectEditor.cancel")}
          </button>
          <button
            type="submit"
            disabled={saving}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? t("projectEditor.saving") : t("projectEditor.save")}
          </button>
        </div>
      </form>
    </div>
  );
}
