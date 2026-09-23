import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { listFiles, uploadFile } from "../lib/filesApi";
import {
  listAssistantKnowledgeFiles,
  attachFileToAssistant,
  detachFileFromAssistant,
} from "../lib/assistantKnowledgeApi";
import {
  listAssistantVersions,
  restoreAssistantVersion,
  compareAssistantVersionWithCurrent,
} from "../lib/assistantVersionsApi";

export default function AssistantEditor({ assistant = null, onClose, onSave, onRestored }) {
  const { t } = useTranslation();
  const isEditing = Boolean(assistant);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [validationError, setValidationError] = useState("");
  const [saving, setSaving] = useState(false);
  const [knowledgeFiles, setKnowledgeFiles] = useState([]);
  const [availableFiles, setAvailableFiles] = useState([]);
  const [knowledgeLoading, setKnowledgeLoading] = useState(false);
  const [knowledgeUploading, setKnowledgeUploading] = useState(false);
  const [versions, setVersions] = useState([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [restoringVersion, setRestoringVersion] = useState(null);
  const [comparingVersion, setComparingVersion] = useState(null);
  const [comparison, setComparison] = useState(null);

  useEffect(() => {
    setName(assistant?.name ?? "");
    setDescription(assistant?.description ?? "");
    setInstructions(assistant?.instructions ?? "");
    setValidationError("");
  }, [assistant]);

  const refreshKnowledge = async () => {
    if (!assistant?.id) return;
    setKnowledgeLoading(true);
    try {
      const [attached, personalFiles] = await Promise.all([
        listAssistantKnowledgeFiles(assistant.id),
        listFiles(),
      ]);
      const attachedIds = new Set(attached.map((file) => file.id));
      setKnowledgeFiles(attached);
      setAvailableFiles(personalFiles.filter((file) => !attachedIds.has(file.id)));
    } catch {
      setKnowledgeFiles([]);
      setAvailableFiles([]);
    } finally {
      setKnowledgeLoading(false);
    }
  };

  useEffect(() => {
    refreshKnowledge();
    if (!assistant?.id) {
      setVersions([]);
      return;
    }
    setVersionsLoading(true);
    listAssistantVersions(assistant.id)
      .then(setVersions)
      .catch(() => setVersions([]))
      .finally(() => setVersionsLoading(false));
  }, [assistant?.id]);

  const compareVersion = async (version) => {
    if (!assistant?.id || comparingVersion !== null) return;
    setComparingVersion(version);
    try {
      const result = await compareAssistantVersionWithCurrent(assistant.id, version);
      setComparison(result);
    } catch {
      setComparison({ error: true });
    } finally {
      setComparingVersion(null);
    }
  };

  const restoreVersion = async (version) => {
    if (!assistant?.id || restoringVersion !== null) return;
    setRestoringVersion(version);
    try {
      const restored = await restoreAssistantVersion(assistant.id, version);
      setName(restored.name);
      setDescription(restored.description ?? "");
      setInstructions(restored.instructions);
      const nextVersions = await listAssistantVersions(assistant.id);
      setVersions(nextVersions);
      onRestored?.(restored);
    } finally {
      setRestoringVersion(null);
    }
  };

  const attachKnowledge = async (fileId) => {
    if (!assistant?.id) return;
    await attachFileToAssistant(assistant.id, fileId);
    await refreshKnowledge();
  };

  const detachKnowledge = async (fileId) => {
    if (!assistant?.id) return;
    await detachFileFromAssistant(assistant.id, fileId);
    await refreshKnowledge();
  };

  const uploadAndAttachKnowledge = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !assistant?.id) return;

    setKnowledgeUploading(true);
    try {
      const uploaded = await uploadFile(file, null, null, null, null);
      await attachFileToAssistant(assistant.id, uploaded.id);
      await refreshKnowledge();
    } finally {
      setKnowledgeUploading(false);
    }
  };

  const submit = async (event) => {
    event.preventDefault();
    const normalizedName = name.trim();
    const normalizedDescription = description.trim();
    const normalizedInstructions = instructions.trim();

    if (!normalizedName || !normalizedInstructions) {
      setValidationError(t("assistantEditor.requiredError"));
      return;
    }

    setValidationError("");
    setSaving(true);
    try {
      await onSave({
        name: normalizedName,
        description: normalizedDescription || null,
        instructions: normalizedInstructions,
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
      aria-labelledby="assistant-editor-title"
    >
      <form
        onSubmit={submit}
        className="max-h-[calc(100dvh-2rem)] w-full max-w-2xl overflow-y-auto rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-slate-700 dark:bg-slate-900"
      >
        <div className="mb-5 flex items-center justify-between gap-4">
          <div>
            <h2 id="assistant-editor-title" className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {isEditing ? t("assistantEditor.editTitle") : t("assistantEditor.createTitle")}
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {t("assistantEditor.subtitle")}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            aria-label={t("assistantEditor.close")}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50 dark:hover:bg-slate-800"
          >
            ✕
          </button>
        </div>

        <div className="space-y-4">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
              {t("assistantEditor.nameLabel")}
            </span>
            <input
              autoFocus
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={100}
              placeholder={t("assistantEditor.namePlaceholder")}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
              {t("assistantEditor.descriptionLabel")}
            </span>
            <input
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={300}
              placeholder={t("assistantEditor.descriptionPlaceholder")}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
              {t("assistantEditor.instructionsLabel")}
            </span>
            <textarea
              value={instructions}
              onChange={(event) => setInstructions(event.target.value)}
              maxLength={6000}
              rows={10}
              placeholder={t("assistantEditor.instructionsPlaceholder")}
              className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
            />
            <span className="mt-1 block text-end text-xs text-slate-400">
              {instructions.length}/6000
            </span>
          </label>

          {isEditing && (
            <section className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
              <div className="mb-3">
                <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                  {t("assistantEditor.versionHistoryTitle")}
                </h3>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  {t("assistantEditor.versionHistorySubtitle")}
                </p>
              </div>
              {versionsLoading ? (
                <p className="text-xs text-slate-400">...</p>
              ) : versions.length === 0 ? (
                <p className="text-xs text-slate-400">
                  {t("assistantEditor.noVersions")}
                </p>
              ) : (
                <div className="max-h-48 space-y-2 overflow-y-auto">
                  {versions.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2 dark:bg-slate-800"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
                          {t("assistantEditor.versionLabel", { version: item.version })}
                        </p>
                        <p className="truncate text-xs text-slate-400">
                          {item.name} · {new Date(item.created_at).toLocaleString()}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => restoreVersion(item.version)}
                        disabled={restoringVersion !== null}
                        className="shrink-0 rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-white disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-900"
                      >
                        {restoringVersion === item.version
                          ? t("assistantEditor.restoring")
                          : t("assistantEditor.restore")}
                      </button>
                      <button
                        type="button"
                        onClick={() => compareVersion(item.version)}
                        disabled={comparingVersion !== null}
                        className="shrink-0 rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-white disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-900"
                      >
                        {comparingVersion === item.version
                          ? t("assistantEditor.comparing")
                          : t("assistantEditor.compare")}
                      </button>
                    </div>
                  ))}
                </div>
              )}
              {comparison && (
                <div className="mt-3 rounded-xl border border-slate-200 bg-slate-950 p-3 text-xs text-slate-100 dark:border-slate-700">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="font-semibold">
                      {comparison.error
                        ? t("assistantEditor.compareError")
                        : t("assistantEditor.compareTitle", {
                            version: comparison.from_version,
                          })}
                    </p>
                    <button
                      type="button"
                      onClick={() => setComparison(null)}
                      className="rounded-lg px-2 py-1 text-slate-300 hover:bg-slate-800"
                    >
                      {t("assistantEditor.closeCompare")}
                    </button>
                  </div>
                  {!comparison.error && (
                    <>
                      <p className="mb-2 text-slate-400">
                        {comparison.changed
                          ? t("assistantEditor.compareChanged")
                          : t("assistantEditor.compareUnchanged")}
                      </p>
                      <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words font-mono leading-5">
                        {comparison.diff || t("assistantEditor.compareNoDiff")}
                      </pre>
                    </>
                  )}
                </div>
              )}
            </section>
          )}

          {isEditing && (
            <section className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    {t("assistantEditor.knowledgeTitle")}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {t("assistantEditor.knowledgeSubtitle")}
                  </p>
                </div>
                <label className="cursor-pointer rounded-xl border border-slate-200 px-3 py-2 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
                  {knowledgeUploading ? t("assistantEditor.uploading") : t("assistantEditor.uploadFile")}
                  <input
                    type="file"
                    className="hidden"
                    onChange={uploadAndAttachKnowledge}
                    disabled={knowledgeUploading}
                  />
                </label>
              </div>

              {knowledgeLoading ? (
                <p className="text-xs text-slate-400">...</p>
              ) : (
                <div className="space-y-2">
                  {knowledgeFiles.length === 0 && availableFiles.length === 0 ? (
                    <p className="text-xs text-slate-400">
                      {t("assistantEditor.noKnowledgeFiles")}
                    </p>
                  ) : null}

                  {knowledgeFiles.map((file) => (
                    <div
                      key={file.id}
                      className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2 dark:bg-slate-800"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-slate-700 dark:text-slate-200">
                          📚 {file.original_filename}
                        </p>
                        <p className="text-xs text-slate-400">
                          {t("assistantEditor.knowledgeAttached")}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => detachKnowledge(file.id)}
                        className="rounded-lg px-2 py-1 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
                      >
                        {t("assistantEditor.detach")}
                      </button>
                    </div>
                  ))}

                  {availableFiles.length > 0 && (
                    <div className="pt-2">
                      <p className="mb-2 text-xs font-medium text-slate-500 dark:text-slate-400">
                        {t("assistantEditor.availableFiles")}
                      </p>
                      <div className="max-h-40 space-y-1 overflow-y-auto">
                        {availableFiles.map((file) => (
                          <button
                            key={file.id}
                            type="button"
                            onClick={() => attachKnowledge(file.id)}
                            className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-start hover:bg-slate-50 dark:hover:bg-slate-800"
                          >
                            <span className="min-w-0 truncate text-sm text-slate-600 dark:text-slate-300">
                              📎 {file.original_filename}
                            </span>
                            <span className="text-xs text-slate-400">
                              {t("assistantEditor.attach")}
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
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
            disabled={saving}
            className="rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            {t("assistantEditor.cancel")}
          </button>
          <button
            type="submit"
            disabled={saving}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? t("assistantEditor.saving") : t("assistantEditor.save")}
          </button>
        </div>
      </form>
    </div>
  );
}
