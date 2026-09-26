import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createConversationComment,
  deleteConversationComment,
  listConversationComments,
  updateConversationComment,
} from "../lib/workspaceConversationCommentsApi";

export default function WorkspaceConversationCommentsPanel({
  workspaceId,
  conversationId,
}) {
  const { t } = useTranslation();
  const [comments, setComments] = useState([]);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editingContent, setEditingContent] = useState("");

  const showErrorToast = (error, fallbackKey) => {
    const message = error?.response?.data?.detail || t(fallbackKey);
    window.dispatchEvent(
      new CustomEvent("app:toast", {
        detail: { message, type: "error" },
      })
    );
  };

  const load = async () => {
    if (!workspaceId || !conversationId) return;
    setLoading(true);
    try {
      setComments(await listConversationComments(workspaceId, conversationId));
    } catch (error) {
      showErrorToast(error, "workspaceComments.loadError");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [workspaceId, conversationId]);

  const handleCreate = async () => {
    const trimmed = content.trim();
    if (!trimmed || submitting) return;

    setSubmitting(true);
    try {
      const comment = await createConversationComment(
        workspaceId,
        conversationId,
        trimmed
      );
      setComments((current) => [...current, comment]);
      setContent("");
    } catch (error) {
      showErrorToast(error, "workspaceComments.saveError");
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdate = async (commentId) => {
    const trimmed = editingContent.trim();
    if (!trimmed || submitting) return;

    setSubmitting(true);
    try {
      const updated = await updateConversationComment(
        workspaceId,
        conversationId,
        commentId,
        trimmed
      );
      setComments((current) =>
        current.map((item) => (item.id === commentId ? updated : item))
      );
      setEditingId(null);
      setEditingContent("");
    } catch (error) {
      showErrorToast(error, "workspaceComments.updateError");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (commentId) => {
    if (submitting) return;
    setSubmitting(true);
    try {
      await deleteConversationComment(workspaceId, conversationId, commentId);
      setComments((current) => current.filter((item) => item.id !== commentId));
    } catch (error) {
      showErrorToast(error, "workspaceComments.deleteError");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mb-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            {t("workspaceComments.title")}
          </h3>
          <p className="mt-1 text-xs text-slate-400">
            {t("workspaceComments.hint")}
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-500 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          {t("workspaceComments.refresh")}
        </button>
      </div>

      <div className="mt-3 max-h-72 space-y-2 overflow-y-auto">
        {loading && comments.length === 0 ? (
          <p className="px-2 py-2 text-xs text-slate-400">...</p>
        ) : comments.length === 0 ? (
          <p className="px-2 py-2 text-xs text-slate-400">
            {t("workspaceComments.empty")}
          </p>
        ) : (
          comments.map((comment) => (
            <div
              key={comment.id}
              className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <span className="block truncate text-xs font-semibold text-slate-700 dark:text-slate-200">
                    {comment.user_email}
                  </span>
                  <span className="text-[11px] text-slate-400">
                    {new Date(comment.created_at).toLocaleString()}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => {
                      setEditingId(comment.id);
                      setEditingContent(comment.content);
                    }}
                    className="rounded-lg px-2 py-1 text-[11px] text-slate-500 hover:bg-white dark:text-slate-300 dark:hover:bg-slate-900"
                  >
                    {t("workspaceComments.edit")}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(comment.id)}
                    disabled={submitting}
                    className="rounded-lg px-2 py-1 text-[11px] text-red-500 hover:bg-red-50 disabled:opacity-50"
                  >
                    {t("workspaceComments.delete")}
                  </button>
                </div>
              </div>

              {editingId === comment.id ? (
                <div className="mt-2 space-y-2">
                  <textarea
                    value={editingContent}
                    onChange={(event) => setEditingContent(event.target.value)}
                    rows={3}
                    maxLength={2000}
                    className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 dark:border-slate-700 dark:bg-slate-900"
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleUpdate(comment.id)}
                      disabled={submitting}
                      className="rounded-xl bg-slate-900 px-3 py-1.5 text-xs text-white disabled:opacity-50"
                    >
                      {t("workspaceComments.save")}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setEditingId(null);
                        setEditingContent("");
                      }}
                      className="rounded-xl border border-slate-200 px-3 py-1.5 text-xs text-slate-600 dark:border-slate-700 dark:text-slate-300"
                    >
                      {t("workspaceComments.cancel")}
                    </button>
                  </div>
                </div>
              ) : (
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700 dark:text-slate-200">
                  {comment.content}
                </p>
              )}
            </div>
          ))
        )}
      </div>

      <div className="mt-3 border-t border-slate-200 pt-3 dark:border-slate-700">
        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          placeholder={t("workspaceComments.placeholder")}
          rows={3}
          maxLength={2000}
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 dark:border-slate-700 dark:bg-slate-900"
        />
        <div className="mt-2 flex items-center justify-between gap-2">
          <span className="text-[11px] text-slate-400">
            {t("workspaceComments.visibility")}
          </span>
          <button
            type="button"
            onClick={handleCreate}
            disabled={submitting || !content.trim()}
            className="rounded-xl bg-slate-900 px-3 py-1.5 text-xs text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {t("workspaceComments.add")}
          </button>
        </div>
      </div>
    </div>
  );
}
