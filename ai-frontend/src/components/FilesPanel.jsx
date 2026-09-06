import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { deleteFile, downloadFile, fetchFileBlob, listFiles, uploadFile } from "../lib/filesApi";
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

export default function FilesPanel({ onClose }) {
  const { t } = useTranslation();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploadProgress, setUploadProgress] = useState(null); // 0-100 أثناء الرفع، null لو ما فيه رفع جارٍ
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState(null); // { url, contentType, name }
  const fileInputRef = useRef(null);

  const refresh = async () => {
    setLoading(true);
    try {
      setFiles(await listFiles());
    } catch {
      setError(t("files.listError"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleUpload = async (fileList) => {
    const file = fileList?.[0];
    if (!file) return;
    setError("");
    setUploadProgress(0);
    try {
      await uploadFile(file, setUploadProgress);
      await refresh();
    } catch (err) {
      setError(getErrorMessage(err, t("files.uploadError")));
    } finally {
      setUploadProgress(null);
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
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/30 p-4">
      <div className="my-8 w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">{t("files.title")}</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

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
          <p className="text-sm text-slate-500">{t("files.dropHint")}</p>
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

        <div className="max-h-72 space-y-2 overflow-y-auto">
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
                  <button
                    onClick={() => handleDelete(file.id)}
                    title={t("files.delete")}
                    className="rounded-lg px-1.5 py-0.5 text-slate-400 hover:bg-red-100 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-slate-400"
                  >
                    ✕
                  </button>
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
          <div className="max-h-[85vh] max-w-3xl overflow-auto rounded-2xl bg-white p-3">
            {preview.contentType.startsWith("image/") ? (
              <img src={preview.url} alt={preview.name} className="max-h-[75vh] rounded-xl" />
            ) : (
              <iframe title={preview.name} src={preview.url} className="h-[75vh] w-[70vw]" />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
