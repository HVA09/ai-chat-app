import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createProjectMemory,
  deleteProjectMemory,
  listProjectMemories,
  updateProjectMemory,
} from "../lib/projectMemoriesApi";

export default function ProjectEditor({
  project = null,
  assistants = [],
  onClose,
  onSave,
}) {
  const { t } = useTranslation();
  const isEditing = Boolean(project);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [assistantId, setAssistantId] = useState("");
  const [validationError, setValidationError] = useState("");
  const [saving, setSaving] = useState(false);
  const [memories, setMemories] = useState([]);
  const [memoryDraft, setMemoryDraft] = useState("");
  const [memoryLoading, setMemoryLoading] = useState(false);
  const [memorySaving, setMemorySaving] = useState(false);
  const [memoryError, setMemoryError] = useState("");

  useEffect(() => {
    setName(project?.name ?? "");
    setDescription(project?.description ?? "");
    setInstructions(project?.instructions ?? "");
    setAssistantId(project?.assistant_id ? String(project.assistant_id) : "");
    setValidationError("");
    setMemoryDraft("");
    setMemoryError("");

    if (!project) {
      setMemories([]);
      return;
    }

    let cancelled = false;
    setMemoryLoading(true);
    listProjectMemories(project.id)
      .then((items) => {
        if (!cancelled) setMemories(items);
      })
      .catch(() => {
        if (!cancelled) setMemoryError(t("projectEditor.memoryLoadError"));
      })
      .finally(() => {
        if (!cancelled) setMemoryLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [project, t]);

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
        assistant_id: assistantId ? Number(assistantId) : null,
      });
    } finally {
      setSaving(false);
    }
  };

  const handleAddMemory = async () => {
    const content = memoryDraft.trim();
    if (!isEditing || !content) return;
    setMemorySaving(true);
    setMemoryError("");
    try {
      const memory = await createProjectMemory(project.id, content);
      setMemories((current) => [memory, ...current]);
      setMemoryDraft("");
    } catch (error) {
      setMemoryError(
        error?.response?.data?.detail || t("projectEditor.memorySaveError")
      );
    } finally {
      setMemorySaving(false);
    }
  };

  const handleEditMemory = async (memory) => {
    if (!isEditing) return;
    const content = window.prompt(
      t("projectEditor.memoryEditPrompt"),
      memory.content
    );
    if (!content?.trim() || content.trim() === memory.content) return;

    setMemorySaving(true);
    setMemoryError("");
    try {
      const updated = await updateProjectMemory(
        project.id,
        memory.id,
        content.trim()
      );
      setMemories((current) =>
        current.map((item) => (item.id === updated.id ? updated : item))
      );
    } catch (error) {
      setMemoryError(
        error?.response?.data?.detail || t("projectEditor.memorySaveError")
      );
    } finally {
      setMemorySaving(false);
    }
  };

  const handleDeleteMemory = async (memory) => {
    if (
      !isEditing ||
      !window.confirm(
        t("projectEditor.memoryDeleteConfirm", { content: memory.content })
      )
    ) {
      return;
    }

    setMemorySaving(true);
    setMemoryError("");
    try {
      await deleteProjectMemory(project.id, memory.id);
      setMemories((current) =>
        current.filter((item) => item.id !== memory.id)
      );
    } catch (error) {
      setMemoryError(
        error?.response?.data?.detail || t("projectEditor.memoryDeleteError")
      );
    } finally {
      setMemorySaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="project-editor-title"
    >
      <form
        onSubmit={submit}
        className="my-8 w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-slate-700 dark:bg-slate-900"
      >
        <div className="mb-5 flex items-center justify-between gap-4">
          <div>
            <h2
              id="project-editor-title"
              className="text-lg font-semibold text-slate-900 dark:text-slate-100"
            >
              {isEditing
                ? t("projectEditor.editTitle")
                : t("projectEditor.createTitle")}
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {t("projectEditor.subtitle")}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={saving || memorySaving}
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
              {t("projectEditor.assistantLabel")}
            </span>
            <select
              value={assistantId}
              onChange={(event) => setAssistantId(event.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
            >
              <option value="">{t("projectEditor.noDefaultAssistant")}</option>
              {assistants.map((assistant) => (
                <option key={assistant.id} value={assistant.id}>
                  {assistant.name}
                </option>
              ))}
            </select>
            <span className="mt-1 block text-xs text-slate-400">
              {t("projectEditor.assistantHint")}
            </span>
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
              {t("projectEditor.instructionsLabel")}
            </span>
            <textarea
              value={instructions}
              onChange={(event) => setInstructions(event.target.value)}
              maxLength={6000}
              rows={8}
              placeholder={t("projectEditor.instructionsPlaceholder")}
              className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
            />
            <span className="mt-1 block text-end text-xs text-slate-400">
              {instructions.length}/6000
            </span>
          </label>

          {isEditing && (
            <section className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {t("projectEditor.memoryTitle")}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {t("projectEditor.memoryDescription")}
                  </p>
                </div>
                <span className="text-xs text-slate-400">
                  {memories.length}/50
                </span>
              </div>

              <div className="space-y-2">
                <textarea
                  value={memoryDraft}
                  onChange={(event) => setMemoryDraft(event.target.value)}
                  maxLength={1000}
                  rows={3}
                  placeholder={t("projectEditor.memoryPlaceholder")}
                  className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
                />
                <button
                  type="button"
                  onClick={handleAddMemory}
                  disabled={
                    memorySaving ||
                    !memoryDraft.trim() ||
                    memories.length >= 50
                  }
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  {memorySaving
                    ? t("projectEditor.memorySaving")
                    : t("projectEditor.memoryAdd")}
                </button>
              </div>

              {memoryLoading ? (
                <p className="mt-3 text-xs text-slate-400">
                  {t("projectEditor.memoryLoading")}
                </p>
              ) : memories.length === 0 ? (
                <p className="mt-3 text-xs text-slate-400">
                  {t("projectEditor.memoryEmpty")}
                </p>
              ) : (
                <div className="mt-3 space-y-2">
                  {memories.map((memory) => (
                    <div
                      key={memory.id}
                      className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800"
                    >
                      <p className="whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-200">
                        {memory.content}
                      </p>
                      <div className="mt-2 flex gap-2">
                        <button
                          type="button"
                          onClick={() => handleEditMemory(memory)}
                          disabled={memorySaving}
                          className="rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-white disabled:opacity-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                        >
                          {t("projectEditor.memoryEdit")}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteMemory(memory)}
                          disabled={memorySaving}
                          className="rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                        >
                          {t("projectEditor.memoryDelete")}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {memoryError && (
                <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                  {memoryError}
                </div>
              )}
            </section>
          )}

          {validationError && (
            <div
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
            >
              {validationError}
            </div>
          )}
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={saving || memorySaving}
            className="rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            {t("projectEditor.cancel")}
          </button>
          <button
            type="submit"
            disabled={saving || memorySaving}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? t("projectEditor.saving") : t("projectEditor.save")}
          </button>
        </div>
      </form>
    </div>
  );
}
