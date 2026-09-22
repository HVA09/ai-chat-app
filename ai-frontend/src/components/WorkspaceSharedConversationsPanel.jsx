import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  listWorkspaceSharedConversations,
  duplicateWorkspaceSharedConversation,
} from "../lib/workspaceConversationSharesApi";

export default function WorkspaceSharedConversationsPanel({
  workspaceId,
  onOpenConversation,
  onDuplicatedConversation = () => {},
}) {
  const { t } = useTranslation();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    if (!workspaceId) {
      setItems([]);
      return undefined;
    }
    setLoading(true);
    listWorkspaceSharedConversations(workspaceId)
      .then((data) => {
        if (active) setItems(data);
      })
      .catch(() => {
        if (active) setItems([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [workspaceId]);

  if (!workspaceId) return null;

  return (
    <div className="mt-3 rounded-xl border border-slate-200 p-2 dark:border-slate-700">
      <div className="mb-2 text-xs font-semibold text-slate-500 dark:text-slate-400">
        {t("workspaceSharing.title")}
      </div>
      {loading ? (
        <p className="px-2 py-1 text-xs text-slate-400">...</p>
      ) : items.length === 0 ? (
        <p className="px-2 py-1 text-xs text-slate-400">
          {t("workspaceSharing.empty")}
        </p>
      ) : (
        <div className="max-h-48 space-y-1 overflow-y-auto">
          {items.map((item) => (
            <div
              key={item.conversation_id}
              className="rounded-lg px-2 py-2 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <button
                type="button"
                onClick={() =>
                  onOpenConversation(item.workspace_id, item.conversation_id)
                }
                className="w-full text-start"
                title={item.title}
              >
                <span className="block truncate text-sm font-medium text-slate-700 dark:text-slate-200">
                  👥 {item.title}
                </span>
                <span className="mt-0.5 block truncate text-xs text-slate-400">
                  {item.shared_by_email}
                </span>
              </button>
              <button
                type="button"
                onClick={async () => {
                  try {
                    const copy = await duplicateWorkspaceSharedConversation(
                      item.workspace_id,
                      item.conversation_id
                    );
                    onDuplicatedConversation(copy.id);
                  } catch {
                    // App handles the user-visible message.
                    onDuplicatedConversation(null);
                  }
                }}
                className="mt-1 rounded-lg border border-slate-200 px-2 py-1 text-[11px] text-slate-500 hover:bg-white dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-900"
              >
                {t("workspaceSharing.duplicateButton")}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
