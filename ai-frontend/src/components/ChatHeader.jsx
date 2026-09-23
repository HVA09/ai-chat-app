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
  onManageShares,
  canManageShares = false,
  onToggleWorkspaceShare,
  canShareWithWorkspace = false,
  workspaceShareActive = false,
  onExportConversation,
  canExportConversation = false,
  onSummarizeConversation,
  canSummarizeConversation = false,
  summaryLoading = false,
  onGenerateConversationTitle,
  canGenerateConversationTitle = false,
  titleLoading = false,
  conversationBranches = [],
  onOpenConversationBranch = () => {},
  parentConversationId = null,
  onOpenParentConversation = () => {},
  isAdmin,
  notifications,
  onMarkNotificationRead,
  onMarkAllNotificationsRead,
}) {
  const { t } = useTranslation();
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [branchMenuOpen, setBranchMenuOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
        <div className="hidden flex-wrap items-center justify-end gap-2 md:flex">
        <div className="flex items-center gap-1">
          <button
            onClick={onToggleWorkspaceShare}
            disabled={!canShareWithWorkspace}
            title={canShareWithWorkspace ? t("workspaceSharing.shareButton") : t("workspaceSharing.shareDisabled")}
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            {workspaceShareActive ? t("workspaceSharing.unshareButton") : t("workspaceSharing.shareButton")}
          </button>
          <button
            onClick={onShareConversation}
            disabled={!canShareConversation}
            title={canShareConversation ? t("sharing.shareButton") : t("sharing.shareDisabled")}
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            {t("sharing.shareButton")}
          </button>
          <button
            onClick={onManageShares}
            disabled={!canManageShares}
            title={canManageShares ? t("sharing.manageButton") : t("sharing.shareDisabled")}
            className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-sm shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ⋯
          </button>
        </div>
        {parentConversationId !== null && (
          <button
            type="button"
            onClick={() => onOpenParentConversation(parentConversationId)}
            title={t("chat.parentConversationTitle")}
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-900"
          >
            {t("chat.parentConversation")}
          </button>
        )}
        <div className="relative">
          <button
            onClick={() => setBranchMenuOpen((open) => !open)}
            disabled={conversationBranches.length === 0}
            title={conversationBranches.length ? t("chat.branchListTitle") : t("chat.branchListEmpty")}
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-900"
          >
            {t("chat.branches")} {conversationBranches.length ? `(${conversationBranches.length})` : ""}
          </button>
          {branchMenuOpen && conversationBranches.length > 0 && (
            <div className="absolute end-0 top-full z-30 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-xl border border-slate-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
              {conversationBranches.map((branch) => (
                <button
                  key={branch.id}
                  type="button"
                  onClick={() => {
                    setBranchMenuOpen(false);
                    onOpenConversationBranch(branch.id);
                  }}
                  className="w-full rounded-lg px-3 py-2 text-start text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  <span className="block truncate font-medium">{branch.title}</span>
                  <span className="mt-0.5 block text-xs text-slate-400">
                    {branch.branched_from_message_index
                      ? t("chat.branchPoint", { index: branch.branched_from_message_index })
                      : ""}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
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
          onClick={onGenerateConversationTitle}
          disabled={!canGenerateConversationTitle || titleLoading}
          title={
            canGenerateConversationTitle
              ? t("conversationTitle.generateButton")
              : t("conversationTitle.disabled")
          }
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:bg-slate-900"
        >
          {titleLoading
            ? t("conversationTitle.loading")
            : t("conversationTitle.generateButton")}
        </button>
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
        <div className="relative md:hidden">
          <button
            type="button"
            onClick={() => setMobileMenuOpen((open) => !open)}
            aria-expanded={mobileMenuOpen}
            aria-label={t("header.more")}
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm dark:border-slate-700 dark:bg-slate-900"
          >
            ⋯
          </button>
          {mobileMenuOpen ? (
            <div className="absolute end-0 top-full z-40 mt-2 w-[min(92vw,22rem)] max-h-[70dvh] overflow-y-auto rounded-2xl border border-slate-200 bg-white p-2 shadow-xl dark:border-slate-700 dark:bg-slate-900">
              <div className="grid grid-cols-2 gap-1">
                <button type="button" onClick={() => { onToggleWorkspaceShare?.(); setMobileMenuOpen(false); }} disabled={!canShareWithWorkspace} className="rounded-xl px-3 py-2 text-start text-sm hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-800">
                  {workspaceShareActive ? t("workspaceSharing.unshareButton") : t("workspaceSharing.shareButton")}
                </button>
                <button type="button" onClick={() => { onShareConversation?.(); setMobileMenuOpen(false); }} disabled={!canShareConversation} className="rounded-xl px-3 py-2 text-start text-sm hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-800">
                  {t("sharing.shareButton")}
                </button>
                <button type="button" onClick={() => setBranchMenuOpen((open) => !open)} disabled={conversationBranches.length === 0} className="rounded-xl px-3 py-2 text-start text-sm hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-800">
                  {t("chat.branches")} {conversationBranches.length ? "(" + conversationBranches.length + ")" : ""}
                </button>
                <button type="button" onClick={() => setExportMenuOpen((open) => !open)} disabled={!canExportConversation} className="rounded-xl px-3 py-2 text-start text-sm hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-800">
                  {t("exportConversation")}
                </button>
                <button type="button" onClick={() => { onGenerateConversationTitle?.(); setMobileMenuOpen(false); }} disabled={!canGenerateConversationTitle || titleLoading} className="rounded-xl px-3 py-2 text-start text-sm hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-800">
                  {titleLoading ? t("conversationTitle.loading") : t("conversationTitle.generateButton")}
                </button>
                <button type="button" onClick={() => { onSummarizeConversation?.(); setMobileMenuOpen(false); }} disabled={!canSummarizeConversation || summaryLoading} className="rounded-xl px-3 py-2 text-start text-sm hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-800">
                  {summaryLoading ? t("summary.loading") : t("summary.button")}
                </button>
                {isAdmin ? (
                  <button type="button" onClick={() => { onOpenAdmin?.(); setMobileMenuOpen(false); }} className="rounded-xl px-3 py-2 text-start text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
                    {t("header.admin")}
                  </button>
                ) : null}
                <button type="button" onClick={() => { onOpenBilling?.(); setMobileMenuOpen(false); }} className="rounded-xl px-3 py-2 text-start text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
                  {t("header.billing")}
                </button>
                <button type="button" onClick={() => { onOpenFiles?.(); setMobileMenuOpen(false); }} className="rounded-xl px-3 py-2 text-start text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
                  {t("header.files")}
                </button>
                <button type="button" onClick={() => { onOpenAccount?.(); setMobileMenuOpen(false); }} className="rounded-xl px-3 py-2 text-start text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
                  {t("header.account")}
                </button>
                <button type="button" onClick={() => { onLogout?.(); setMobileMenuOpen(false); }} className="rounded-xl px-3 py-2 text-start text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30">
                  {t("logout")}
                </button>
              </div>
              {branchMenuOpen && conversationBranches.length > 0 ? (
                <div className="mt-2 rounded-xl border border-slate-200 p-1 dark:border-slate-700">
                  {conversationBranches.map((branch) => (
                    <button key={branch.id} type="button" onClick={() => { setBranchMenuOpen(false); setMobileMenuOpen(false); onOpenConversationBranch(branch.id); }} className="w-full rounded-lg px-3 py-2 text-start text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
                      <span className="block truncate font-medium">{branch.title}</span>
                    </button>
                  ))}
                </div>
              ) : null}
              {exportMenuOpen && canExportConversation ? (
                <div className="mt-2 rounded-xl border border-slate-200 p-1 dark:border-slate-700">
                  <button type="button" onClick={() => { setExportMenuOpen(false); setMobileMenuOpen(false); onExportConversation("markdown"); }} className="w-full rounded-lg px-3 py-2 text-start text-sm hover:bg-slate-100 dark:hover:bg-slate-800">{t("exportMarkdown")}</button>
                  <button type="button" onClick={() => { setExportMenuOpen(false); setMobileMenuOpen(false); onExportConversation("json"); }} className="w-full rounded-lg px-3 py-2 text-start text-sm hover:bg-slate-100 dark:hover:bg-slate-800">{t("exportJson")}</button>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
