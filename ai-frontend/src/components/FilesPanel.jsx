import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  attachFileToConversation,
  deleteFile,
  detachFileFromConversation,
  downloadFile,
  fetchFileBlob,
  listFiles,
  uploadFile,
  indexImageForRag,
} from "../lib/filesApi";
import { getErrorMessage } from "../lib/errors";

const ICONS = {
  "image/jpeg": "🖼️",
  "image/png": "🖼️",
  "image/gif": "🖼️",
  "image/webp": "🖼️",
  "application/pdf": "📄",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "📝",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "📊",
  "text/plain": "📄",
  "text/csv": "📊",
  "application/vnd.ms-excel": "📊",
};

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FilesPanel({
  onClose,
  conversationId = null,
  workspaceId = null,
  projectId = null,
  onAnalyzeImage,
}) {
  const { t } = useTranslation();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploadProgress, setUploadProgress] = useState(null); // 0-100 أثناء الرفع، null لو ما فيه رفع جارٍ
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState(null); // { url, contentType, name }
  const [analyzingId, setAnalyzingId] = useState(null);
  const [indexingId, setIndexingId] = useState(null);
  const [showWorkspaceFiles, setShowWorkspaceFiles] = useState(false);
  const [showProjectFiles, setShowProjectFiles] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (projectId !== null) {
      setShowProjectFiles(true);
      setShowWorkspaceFiles(false);
    } else if (workspaceId !== null) {
      setShowProjectFiles(false);
      setShowWorkspaceFiles(true);
    } else {
      setShowProjectFiles(false);
      setShowWorkspaceFiles(false);
    }
  }, [workspaceId, projectId]);

  const refresh = async () => {
    setLoading(true);
    try {
      setFiles(
        await listFiles(
          showProjectFiles || showWorkspaceFiles ? null : conversationId,
          showProjectFiles || showWorkspaceFiles ? false : Boolean(conversationId),
          showProjectFiles || showWorkspaceFiles ? workspaceId : null,
          showProjectFiles ? projectId : null
        )
      );
    } catch {
      setError(t("files.listError"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, [conversationId, showWorkspaceFiles, showProjectFiles, workspaceId, projectId]);

  const filteredFiles = files.filter((file) =>
    file.original_filename
      .toLocaleLowerCase()
      .includes(searchQuery.trim().toLocaleLowerCase())
  );

  const handleUpload = async (fileList) => {
    const selectedFiles = Array.from(fileList || []).filter(Boolean);
    if (!selectedFiles.length) return;

    setError("");
    let completed = 0;
    let failed = 0;

    for (const file of selectedFiles) {
      try {
        setUploadProgress(Math.round((completed / selectedFiles.length) * 100));
        await uploadFile(
          file,
          (progress) => {
            const overall = ((completed + progress / 100) / selectedFiles.length) * 100;
            setUploadProgress(Math.round(overall));
          },
          showProjectFiles || showWorkspaceFiles ? null : conversationId,
          showProjectFiles || showWorkspaceFiles ? workspaceId : null,
          showProjectFiles ? projectId : null
        );
      } catch (err) {
        failed += 1;
        setError(
          getErrorMessage(
            err,
            t("files.uploadErrorForFile", { name: file.name })
          )
        );
      } finally {
        completed += 1;
      }
    }

    setUploadProgress(100);
    try {
      await refresh();
    } finally {
      window.setTimeout(() => setUploadProgress(null), 250);
    }

    if (failed === 0 && selectedFiles.length > 1) {
      setError("");
    }
  };

  const handleToggleAttachment = async (file) => {
    if (!conversationId) return;
    try {
      if (file.is_attached) {
        await detachFileFromConversation(file.id, conversationId);
      } else {
        await attachFileToConversation(file.id, conversationId);
      }
      await refresh();
    } catch (err) {
      setError(getErrorMessage(err, t("files.attachmentError")));
    }
  };

  const handleAnalyzeImage = async (file) => {
    if (!conversationId || !file.content_type.startsWith("image/") || !onAnalyzeImage) return;
    const prompt = window.prompt(t("files.analyzePrompt"));
    if (!prompt?.trim()) return;

    setError("");
    setAnalyzingId(file.id);
    try {
      await onAnalyzeImage(file, prompt.trim());
    } catch (err) {
      setError(getErrorMessage(err, t("files.imageAnalyzeError")));
    } finally {
      setAnalyzingId(null);
    }
  };

  const handleIndexImage = async (file) => {
    if (!file.content_type.startsWith("image/") || file.is_ai_indexed) return;

    setError("");
    setIndexingId(file.id);
    try {
      await indexImageForRag(file.id);
      await refresh();
    } catch (err) {
      setError(getErrorMessage(err, t("files.imageIndexError")));
    } finally {
      setIndexingId(null);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm(t("files.confirmDelete"))) return;
    try {
      await deleteFile(id);
      setFiles((prev) => prev.filter((f) => f.id !== id));
    } catch {
      setError(t("files.deleteError"));
    }
  };

  const handlePreview = async (file) => {
    const previewable =
      file.content_type.startsWith("image/") || file.content_type === "application/pdf";
    if (!previewable) {
      downloadFile(file.id, file.original_filename);
      return;
    }
    try {
      const blob = await fetchFileBlob(file.id);
      const url = window.URL.createObjectURL(blob);
      setPreview({ url, contentType: file.content_type, name: file.original_filename });
    } catch {
      setError(t("files.previewError"));
    }
  };

  const closePreview = () => {
    if (preview) window.URL.revokeObjectURL(preview.url);
    setPreview(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/40 p-2 sm:p-4">
      <div className="my-0 flex max-h-[calc(100dvh-1rem)] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900 sm:my-8 sm:max-h-[calc(100dvh-3rem)] sm:rounded-3xl">
        <div className="border-b border-slate-200 px-4 pb-3 pt-4 dark:border-slate-700 sm:px-6 sm:pt-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="truncate text-lg font-semibold text-slate-900 dark:text-slate-100">
                {showProjectFiles
                  ? t("files.projectTitle")
                  : showWorkspaceFiles
                    ? t("files.workspaceTitle")
                    : t("files.title")}
              </h2>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                {t("files.libraryCount", { count: files.length })}
              </p>
            </div>
            <button
              onClick={onClose}
              aria-label={t("files.close")}
              className="rounded-xl border border-slate-200 px-2.5 py-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            >
              ✕
            </button>
          </div>

        {(workspaceId !== null || projectId !== null) && (
          <div className={`mb-4 grid ${projectId !== null ? "grid-cols-3" : "grid-cols-2"} gap-2 rounded-xl border border-slate-200 p-1 dark:border-slate-700`}>
            <button
              type="button"
              onClick={() => {
                setShowWorkspaceFiles(false);
                setShowProjectFiles(false);
              }}
              className={`rounded-lg px-2 py-2 text-xs font-medium ${!showWorkspaceFiles && !showProjectFiles ? "bg-slate-900 text-white" : "text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800"}`}
            >
              {t("files.myFiles")}
            </button>
            {workspaceId !== null && (
              <button
                type="button"
                onClick={() => {
                  setShowProjectFiles(false);
                  setShowWorkspaceFiles(true);
                }}
                className={`rounded-lg px-2 py-2 text-xs font-medium ${showWorkspaceFiles ? "bg-slate-900 text-white" : "text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800"}`}
              >
                {t("files.workspaceFiles")}
              </button>
            )}
            {projectId !== null && (
              <button
                type="button"
                onClick={() => {
                  setShowWorkspaceFiles(false);
                  setShowProjectFiles(true);
                }}
                className={`rounded-lg px-2 py-2 text-xs font-medium ${showProjectFiles ? "bg-slate-900 text-white" : "text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800"}`}
              >
                {t("files.projectFiles")}
              </button>
            )}
          </div>
        )}

        <div className="px-4 pt-3 sm:px-6">
          <label className="relative block">
            <span className="sr-only">{t("files.searchPlaceholder")}</span>
            <input
              type="search"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder={t("files.searchPlaceholder")}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-10 py-2.5 text-sm text-slate-700 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
            <span className="pointer-events-none absolute inset-y-0 start-3 flex items-center text-slate-400" aria-hidden="true">⌕</span>
          </label>
        </div>

        {showWorkspaceFiles && workspaceId === null ? (
          <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            {t("files.workspaceUnavailable")}
          </div>
        ) : null}

        <div className="px-4 pt-3 sm:px-6">
        {/* منطقة السحب والإفلات */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            handleUpload(e.dataTransfer.files);
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`mb-4 cursor-pointer rounded-2xl border-2 border-dashed p-6 text-center transition-colors ${
            dragOver ? "border-slate-400 bg-slate-50" : "border-slate-200"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".txt,.csv,.pdf,.docx,.xlsx,.xls,image/jpeg,image/png,image/gif,image/webp"
            className="hidden"
            onChange={(e) => {
              handleUpload(e.target.files);
              e.target.value = "";
            }}
          />
          <p className="text-sm text-slate-500">
            {showProjectFiles
              ? t("files.projectDropHint")
              : showWorkspaceFiles
                ? t("files.workspaceDropHint")
                : t("files.dropHint")}
          </p>
          <p className="mt-1 text-xs text-slate-400">{t("files.typesHint")}</p>
        </div>
        </div>

        {uploadProgress !== null && (
          <div className="mb-4">
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full bg-slate-900 transition-all"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <p className="mt-1 text-center text-xs text-slate-400">{uploadProgress}%</p>
          </div>
        )}

        {error && (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4 pe-1 sm:px-6 sm:max-h-[52dvh]">
          {loading ? (
            <p className="text-sm text-slate-400">...</p>
          ) : filteredFiles.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-10 text-center dark:border-slate-700">
              <div className="text-3xl">📁</div>
              <p className="mt-2 text-sm font-medium text-slate-700 dark:text-slate-200">
                {files.length ? t("files.noSearchResults") : t("files.noFiles")}
              </p>
              <p className="mt-1 text-xs text-slate-400">
                {files.length ? t("files.tryDifferentSearch") : t("files.emptyHint")}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
            {filteredFiles.map((file) => (
              <div
                key={file.id}
                className="rounded-2xl border border-slate-200 bg-white p-3 transition hover:border-slate-300 hover:shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:hover:border-slate-600"
              >
                <button
                  onClick={() => handlePreview(file)}
                  className="flex min-w-0 flex-1 items-center gap-2 text-start"
                >
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-lg dark:bg-slate-800">
                    {ICONS[file.content_type] || "📎"}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-slate-900 dark:text-slate-100">
                      {file.original_filename}
                    </span>
                    <span className="mt-0.5 block text-xs text-slate-400">
                      {formatSize(file.size_bytes)} · {new Date(file.created_at).toLocaleDateString()}
                    </span>
                  </span>
                </button>
                <div className="flex shrink-0 items-center gap-1">
                  <button
                    onClick={() => downloadFile(file.id, file.original_filename)}
                    title={t("files.download")}
                    className="rounded-lg px-1.5 py-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400"
                  >
                    ⬇
                  </button>
                  {file.content_type.startsWith("image/") && (
                    <button
                      onClick={() => handleIndexImage(file)}
                      disabled={Boolean(file.is_ai_indexed) || indexingId === file.id}
                      title={file.is_ai_indexed ? t("files.imageIndexed") : t("files.indexImageForAi")}
                      className="rounded-lg px-1.5 py-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-slate-400"
                    >
                      {indexingId === file.id ? "..." : file.is_ai_indexed ? "✅" : "✨"}
                    </button>
                  )}
                  {conversationId && file.is_attached && file.content_type.startsWith("image/") && onAnalyzeImage && (
                    <button
                      onClick={() => handleAnalyzeImage(file)}
                      disabled={analyzingId === file.id}
                      title={t("files.analyzeImage")}
                      className="rounded-lg px-1.5 py-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-slate-400"
                    >
                      {analyzingId === file.id ? "..." : "🔎"}
                    </button>
                  )}
                  {!showWorkspaceFiles && !showProjectFiles && conversationId && (
                    <button
                      onClick={() => handleToggleAttachment(file)}
                      title={file.is_attached ? t("files.detach") : t("files.attach")}
                      className="rounded-lg px-1.5 py-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400"
                    >
                      {file.is_attached ? "↩" : "＋"}
                    </button>
                  )}
                  {file.can_delete && (
                  <button
                    onClick={() => handleDelete(file.id)}
                    title={t("files.delete")}
                    className="rounded-lg px-1.5 py-0.5 text-slate-400 hover:bg-red-100 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-slate-400"
                  >
                    ✕
                  </button>
                  )}
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-1.5 ps-[3.25rem] text-[11px] text-slate-400">
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 dark:bg-slate-800">
                    {file.workspace_id !== null
                      ? file.project_id !== null
                        ? t("files.scopeProject")
                        : t("files.scopeWorkspace")
                      : t("files.scopePersonal")}
                  </span>
                  {file.is_attached ? (
                    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                      {t("files.attached")}
                    </span>
                  ) : null}
                  {file.is_ai_indexed ? (
                    <span className="rounded-full bg-blue-50 px-2 py-0.5 text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                      {t("files.indexed")}
                    </span>
                  ) : null}
                </div>
              </div>
            ))}
            </div>
          )}
        </div>
        <div className="border-t border-slate-200 px-4 py-3 dark:border-slate-700 sm:px-6">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="w-full rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          >
            + {t("files.addMore")}
          </button>
        </div>
      </div>

      {preview && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4"
          onClick={closePreview}
        >
          <div className="max-h-[calc(100dvh-1rem)] w-full max-w-3xl overflow-auto rounded-2xl bg-white p-2 sm:p-3">
            {preview.contentType.startsWith("image/") ? (
              <img src={preview.url} alt={preview.name} className="max-h-[80dvh] max-w-full rounded-xl object-contain" />
            ) : (
              <iframe title={preview.name} src={preview.url} className="h-[80dvh] w-full sm:w-[70vw]" />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
