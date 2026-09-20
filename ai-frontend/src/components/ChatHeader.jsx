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
  isAdmin,
  notifications,
  onMarkNotificationRead,
  onMarkAllNotificationsRead,
}) {
  const { t } = useTranslation();

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
