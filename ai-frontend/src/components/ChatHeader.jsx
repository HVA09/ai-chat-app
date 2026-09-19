import { useState } from "react";
import LanguageToggle from "./LanguageToggle";
import ThemeToggle from "./ThemeToggle";
import NotificationBell from "./NotificationBell";
import { useTranslation } from "react-i18next";

export default function ChatHeader({
  lang,
  setLang,
  onLogout,
  onOpenAccount,
  onOpenFiles,
  onOpenAdmin,
  onOpenBilling,
  onShareConversation,
  canShareConversation = false,
  onExportConversation,
  canExportConversation = false,
  onSummarizeConversation,
  canSummarizeConversation = false,
  summaryLoading = false,
  isAdmin,
  notifications,
  onMarkNotificationRead,
  onMarkAllNotificationsRead,
}) {
  const { t } = useTranslation();
  const [exportMenuOpen, setExportMenuOpen] = useState(false);

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white py-3 pe-4 ps-16 dark:border-slate-700 dark:bg-slate-900 md:ps-4">
      <div>
        <h2 className="text-lg font-semibold">{t("appName")}</h2>
        <p className="hidden text-sm text-slate-500 sm:block">{t("emptyDesc")}</p>
      </div>
      <div className="flex flex-wrap items-center justify-end gap-2 sm:gap-3">
        <LanguageToggle lang={lang} setLang={setLang} />
        <ThemeToggle />
        <NotificationBell
          notifications={notifications}
          onMarkRead={onMarkNotificationRead}
          onMarkAllRead={onMarkAllNotificationsRead}
        />
        <button
          onClick={onShareConversation}
          disabled={!canShareConversation}
          title={canShareConversation ? t("sharing.shareButton") : t("sharing.shareDisabled")}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          {t("sharing.shareButton")}
        </button>
        <div className="relative">
          <button
            onClick={() => setExportMenuOpen((open) => !open)}
            disabled={!canExportConversation}
            title={canExportConversation ? t("exportConversation") : t("exportConversationDisabled")}
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-900"
          >
            {t("exportConversation")} ▾
          </button>
          {exportMenuOpen && canExportConversation && (
            <div className="absolute end-0 top-full z-30 mt-2 w-40 rounded-xl border border-slate-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
              <button
                type="button"
                onClick={() => {
                  setExportMenuOpen(false);
                  onExportConversation("markdown");
                }}
                className="w-full rounded-lg px-3 py-2 text-start text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                {t("exportMarkdown")}
              </button>
              <button
                type="button"
                onClick={() => {
                  setExportMenuOpen(false);
                  onExportConversation("json");
                }}
                className="w-full rounded-lg px-3 py-2 text-start text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                {t("exportJson")}
              </button>
            </div>
          )}
        </div>
        <button
          onClick={onSummarizeConversation}
          disabled={!canSummarizeConversation || summaryLoading}
          title={canSummarizeConversation ? t("summary.button") : t("summary.disabled")}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-900"
        >
          {summaryLoading ? t("summary.loading") : t("summary.button")}
        </button>
        {isAdmin && (
          <button
            onClick={onOpenAdmin}
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            {t("header.admin")}
          </button>
        )}
        <button
          onClick={onOpenBilling}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          {t("header.billing")}
        </button>
        <button
          onClick={onOpenFiles}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          {t("header.files")}
        </button>
        <button
          onClick={onOpenAccount}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          {t("header.account")}
        </button>
        <button
          onClick={onLogout}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
        >
          {t("logout")}
        </button>
      </div>
    </header>
  );
}
