import { useState } from "react";
import { useTranslation } from "react-i18next";

export default function NotificationBell({ notifications, onMarkRead, onMarkAllRead }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
      >
        🔔
        {unreadCount > 0 && (
          <span className="absolute -top-1 -end-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute end-0 z-50 mt-2 w-72 rounded-2xl border border-slate-200 bg-white p-2 shadow-lg">
            <div className="flex items-center justify-between px-2 py-1">
              <p className="text-sm font-medium text-slate-900">{t("notif.title")}</p>
              {unreadCount > 0 && (
                <button
                  onClick={onMarkAllRead}
                  className="text-xs text-slate-500 hover:text-slate-700"
                >
                  {t("notif.markAllRead")}
                </button>
              )}
            </div>
            <div className="max-h-80 space-y-1 overflow-y-auto">
              {notifications.length === 0 ? (
                <p className="px-2 py-3 text-center text-sm text-slate-400">{t("notif.empty")}</p>
              ) : (
                notifications.map((n) => (
                  <button
                    key={n.id}
                    onClick={() => !n.is_read && onMarkRead(n.id)}
                    className={`block w-full rounded-xl px-2 py-2 text-start text-sm hover:bg-slate-50 ${
                      n.is_read ? "text-slate-500" : "bg-slate-50 text-slate-900"
                    }`}
                  >
                    <p className="font-medium">{n.title}</p>
                    <p className="text-xs text-slate-500">{n.body}</p>
                  </button>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
