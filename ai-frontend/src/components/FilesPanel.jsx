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
  "text/csv": "📊",
  "application/vnd.ms-excel": "📊",
};

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FilesPanel({ onClose, conversationId = null, workspaceId = null, onAnalyzeImage }) {
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
  const fileInputRef = useRef(null);

  const refresh = async () => {
    setLoading(true);
    try {
      setFiles(
        await listFiles(
          showWorkspaceFiles ? null : conversationId,
          showWorkspaceFiles ? false : Boolean(conversationId),
          showWorkspaceFiles ? workspaceId : null
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
  }, [conversationId, showWorkspaceFiles, workspaceId]);

  const handleUpload = async (fileList) => {
    const file = fileList?.[0];
    if (!file) return;
    setError("");
    setUploadProgress(0);
    try {
      await uploadFile(
        file,
        setUploadProgress,
        showWorkspaceFiles ? null : conversationId,
        showWorkspaceFiles ? workspaceId : null
      );
      await refresh();
    } catch (err) {
      setError(getErrorMessage(err, t("files.uploadError")));
    } finally {
      setUploadProgress(null);
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
      <div className="my-0 flex max-h-[calc(100dvh-1rem)] w-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 shadow-lg dark:border-slate-700 dark:bg-slate-900 sm:my-8 sm:max-h-[calc(100dvh-3rem)] sm:max-w-lg sm:rounded-3xl sm:p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">
            {showWorkspaceFiles ? t("files.workspaceTitle") : t("files.title")}
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

        {workspaceId !== null && (
          <div className="mb-4 grid grid-cols-2 gap-2 rounded-xl border border-slate-200 p-1 dark:border-slate-700">
            <button
              type="button"
              onClick={() => setShowWorkspaceFiles(false)}
              className={`rounded-lg px-3 py-2 text-xs font-medium ${!showWorkspaceFiles ? "bg-slate-900 text-white" : "text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800"}`}
            >
              {t("files.myFiles")}
            </button>
            <button
              type="button"
              onClick={() => setShowWorkspaceFiles(true)}
              className={`rounded-lg px-3 py-2 text-xs font-medium ${showWorkspaceFiles ? "bg-slate-900 text-white" : "text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800"}`}
            >
              {t("files.workspaceFiles")}
            </button>
          </div>
        )}

        {showWorkspaceFiles && workspaceId === null ? (
          <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            {t("files.workspaceUnavailable")}
          </div>
        ) : null}

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
            className="hidden"
            onChange={(e) => handleUpload(e.target.files)}
          />
          <p className="text-sm text-slate-500">
            {showWorkspaceFiles ? t("files.workspaceDropHint") : t("files.dropHint")}
          </p>
          <p className="mt-1 text-xs text-slate-400">{t("files.typesHint")}</p>
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

        <div className="min-h-0 max-h-[45dvh] space-y-2 overflow-y-auto pe-1 sm:max-h-72">
          {loading ? (
            <p className="text-sm text-slate-400">...</p>
          ) : files.length === 0 ? (
            <p className="text-sm text-slate-400">{t("files.noFiles")}</p>
          ) : (
            files.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between gap-2 rounded-xl border border-slate-200 px-3 py-2"
              >
                <button
                  onClick={() => handlePreview(file)}
                  className="flex min-w-0 flex-1 items-center gap-2 text-start"
                >
                  <span className="text-lg">{ICONS[file.content_type] || "📎"}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm text-slate-900">
                      {file.original_filename}
                    </span>
                    <span className="text-xs text-slate-400">{formatSize(file.size_bytes)}</span>
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
                  {!showWorkspaceFiles && conversationId && (
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
              </div>
            ))
          )}
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
