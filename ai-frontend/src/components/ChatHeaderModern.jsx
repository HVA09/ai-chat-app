import { useState } from "react";
import { useTranslation } from "react-i18next";
import LanguageToggle from "./LanguageToggle";
import ThemeToggle from "./ThemeToggle";
import NotificationBell from "./NotificationBell";
import Icon from "./ui/Icon";

export default function ChatHeaderModern({
  conversationTitle = "",
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
  const [menuOpen, setMenuOpen] = useState(false);
  const [branchOpen, setBranchOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const openSidebar = () => window.dispatchEvent(new CustomEvent("app:open-sidebar"));

  return (
    <header className="modern-chat-header">
      <button
        type="button"
        className="modern-header-mobile-menu md:hidden"
        onClick={openSidebar}
        aria-label={lang === "ar" ? "فتح القائمة" : "Open navigation"}
        title={lang === "ar" ? "فتح القائمة" : "Open navigation"}
      >
        <Icon name="menu" size={19} />
      </button>

      <div className="min-w-0">
        <div className="flex items-center gap-3">
          <div className="modern-chat-status-dot" />
          <div className="min-w-0">
            <h2 className="truncate text-[15px] font-semibold text-slate-900 dark:text-slate-100">
              {conversationTitle || t("newChat")}
            </h2>
            <p className="truncate text-[11px] text-slate-400">{t("appName")}</p>
          </div>
        </div>
      </div>

      <div className="modern-header-actions flex items-center gap-1.5">
        <div className="modern-header-preferences hidden items-center gap-1.5 sm:flex">
          <LanguageToggle lang={lang} setLang={setLang} />
          <ThemeToggle />
        </div>
        <NotificationBell
          notifications={notifications}
          onMarkRead={onMarkNotificationRead}
          onMarkAllRead={onMarkAllNotificationsRead}
        />

        <div className="relative">
          <button
            type="button"
            onClick={() => { setSettingsOpen((value) => !value); setMenuOpen(false); }}
            className="modern-header-icon-action"
            aria-label={lang === "ar" ? "الإعدادات" : "Settings"}
            aria-expanded={settingsOpen}
            title={lang === "ar" ? "الإعدادات" : "Settings"}
          >
            <Icon name="settings" size={18} />
          </button>
          {settingsOpen ? (
            <div className="modern-header-menu modern-settings-menu">
              <div className="modern-header-menu-label">{lang === "ar" ? "الإعدادات" : "Settings"}</div>
              <div className="flex items-center justify-between gap-3 px-3 py-2">
                <LanguageToggle lang={lang} setLang={setLang} />
                <ThemeToggle />
              </div>
              <div className="modern-header-menu-divider" />
              <button type="button" onClick={() => { onOpenAccount?.(); setSettingsOpen(false); }} className="modern-header-menu-item">{t("header.account")}</button>
              <button type="button" onClick={() => { onOpenFiles?.(); setSettingsOpen(false); }} className="modern-header-menu-item">{t("header.files")}</button>
              <button type="button" onClick={() => { onOpenBilling?.(); setSettingsOpen(false); }} className="modern-header-menu-item">{t("header.billing")}</button>
              {isAdmin ? <button type="button" onClick={() => { onOpenAdmin?.(); setSettingsOpen(false); }} className="modern-header-menu-item">{t("header.admin")}</button> : null}
              <div className="modern-header-menu-divider" />
              <button type="button" onClick={() => { onLogout?.(); setSettingsOpen(false); }} className="modern-header-menu-item danger">{t("logout")}</button>
            </div>
          ) : null}
        </div>

        {conversationBranches.length > 0 ? (
          <div className="relative hidden sm:block">
            <button type="button" onClick={() => setBranchOpen((value) => !value)} className="modern-header-icon-action" title={t("chat.branchListTitle")}>
              <Icon name="gitBranch" size={18} />
            </button>
            {branchOpen ? (
              <div className="modern-header-menu">
                {parentConversationId !== null ? (
                  <button type="button" onClick={() => { setBranchOpen(false); onOpenParentConversation(parentConversationId); }} className="modern-header-menu-item">{t("chat.parentConversation")}</button>
                ) : null}
                {conversationBranches.map((branch) => (
                  <button key={branch.id} type="button" onClick={() => { setBranchOpen(false); onOpenConversationBranch(branch.id); }} className="modern-header-menu-item"><span className="truncate">{branch.title}</span></button>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="relative">
          <button type="button" onClick={() => { setMenuOpen((value) => !value); setSettingsOpen(false); }} className="modern-header-more" aria-label={t("header.more")} aria-expanded={menuOpen}>
            <Icon name="more" size={18} />
          </button>
          {menuOpen ? (
            <div className="modern-header-menu modern-header-menu-wide">
              <div className="modern-header-menu-label">{lang === "ar" ? "المحادثة" : "Conversation"}</div>
              <button type="button" disabled={!canShareConversation} onClick={() => { onShareConversation?.(); setMenuOpen(false); }} className="modern-header-menu-item">{t("sharing.shareButton")}</button>
              <button type="button" disabled={!canManageShares} onClick={() => { onManageShares?.(); setMenuOpen(false); }} className="modern-header-menu-item">{t("sharing.manageButton")}</button>
              <button type="button" disabled={!canShareWithWorkspace} onClick={() => { onToggleWorkspaceShare?.(); setMenuOpen(false); }} className="modern-header-menu-item">{workspaceShareActive ? t("workspaceSharing.unshareButton") : t("workspaceSharing.shareButton")}</button>
              <button type="button" disabled={!canExportConversation} onClick={() => { onExportConversation?.("markdown"); setMenuOpen(false); }} className="modern-header-menu-item">{t("exportMarkdown")}</button>
              <button type="button" disabled={!canExportConversation} onClick={() => { onExportConversation?.("json"); setMenuOpen(false); }} className="modern-header-menu-item">{t("exportJson")}</button>
              <button type="button" disabled={!canGenerateConversationTitle || titleLoading} onClick={() => { onGenerateConversationTitle?.(); setMenuOpen(false); }} className="modern-header-menu-item">{titleLoading ? t("conversationTitle.loading") : t("conversationTitle.generateButton")}</button>
              <button type="button" disabled={!canSummarizeConversation || summaryLoading} onClick={() => { onSummarizeConversation?.(); setMenuOpen(false); }} className="modern-header-menu-item">{summaryLoading ? t("summary.loading") : t("summary.button")}</button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
