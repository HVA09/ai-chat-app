import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { listConversationShares, revokeConversationShare } from "../lib/sharedConversationsApi";

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

export default function ConversationShareManager({ conversationId, onClose, onChanged }) {
  const { t } = useTranslation();
  const [shares, setShares] = useState([]);
  const [loading, setLoading] = useState(true);
  const [revokingId, setRevokingId] = useState(null);
  const [error, setError] = useState("");

  const refresh = async () => {
    if (!conversationId) return;
    setLoading(true);
    setError("");
    try {
      setShares(await listConversationShares(conversationId));
    } catch (err) {
      setError(err?.response?.data?.detail || t("sharing.managementLoadError"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, [conversationId]);

  const handleRevoke = async (shareId) => {
    if (!window.confirm(t("sharing.revokeConfirm"))) return;
    setRevokingId(shareId);
    try {
      await revokeConversationShare(conversationId, shareId);
      await refresh();
      onChanged?.();
    } catch (err) {
      setError(err?.response?.data?.detail || t("sharing.revokeError"));
    } finally {
      setRevokingId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="share-manager-title"
        className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-5 shadow-xl dark:border-slate-700 dark:bg-slate-900"
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 id="share-manager-title" className="text-lg font-semibold">
              {t("sharing.managementTitle")}
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {t("sharing.managementHint")}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            ✕
          </button>
        </div>

        <div className="mt-4">
          {loading ? (
            <p className="text-sm text-slate-400">{t("sharing.managementLoading")}</p>
          ) : error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          ) : shares.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-200 p-4 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
              {t("sharing.noActiveLinks")}
            </p>
          ) : (
            <div className="space-y-2">
              {shares.map((share) => (
                <div
                  key={share.id}
                  className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
                      <span>
                        {share.is_expired ? t("sharing.expiredLink") : t("sharing.activeLink")}
                      </span>
                      {share.password_protected ? (
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                          {t("sharing.passwordProtected")}
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      {t("sharing.createdAt", { date: formatDate(share.created_at) })}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      {t("sharing.expiresAt", {
                        date: share.expires_at ? formatDate(share.expires_at) : t("sharing.never"),
                      })}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRevoke(share.id)}
                    disabled={revokingId === share.id}
                    className="shrink-0 rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
                  >
                    {revokingId === share.id ? t("sharing.revoking") : t("sharing.revoke")}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
