import { useTranslation } from "react-i18next";

export default function useCommandPaletteActions({
  startNewChat,
  showArchivedConversations,
  setShowArchivedConversations,
  showTrashConversations,
  setShowTrashConversations,
  selectedFolderId,
  selectedWorkspaceId,
  selectedProjectId,
  conversationSearch,
  setSelectedFolderId,
  setSelectedConversationIds,
  refreshConversations,
  setShowFiles,
  setShowAccountSettings,
  setShowBilling,
  handleCreateFolder,
  handleCreateProject,
  openCreateAssistantEditor,
  setShowScheduledTasks,
  currentUserRole,
  setShowAdmin,
}) {
  const { t } = useTranslation();

  return [
    {
      id: "new-chat",
      label: t("commandPalette.actions.newChat"),
      keywords: ["new", "chat", "محادثة"],
      icon: "＋",
      onSelect: startNewChat,
    },
    {
      id: "archived",
      label: showArchivedConversations
        ? t("commandPalette.actions.backToChats")
        : t("commandPalette.actions.archived"),
      keywords: ["archive", "archived", "أرشيف", "المؤرشفة"],
      icon: "▱",
      onSelect: () => {
        const next = !showArchivedConversations;
        setShowArchivedConversations(next);
        setShowTrashConversations(false);
        refreshConversations(
          next,
          selectedFolderId,
          selectedWorkspaceId,
          selectedProjectId,
          conversationSearch,
          false
        );
        if (next) startNewChat();
      },
    },
    {
      id: "trash",
      label: showTrashConversations
        ? t("commandPalette.actions.backToChats")
        : t("commandPalette.actions.trash"),
      keywords: ["trash", "deleted", "سلة", "محذوفة"],
      icon: "🗑",
      onSelect: () => {
        const next = !showTrashConversations;
        setShowTrashConversations(next);
        setShowArchivedConversations(false);
        setSelectedFolderId(null);
        setSelectedConversationIds([]);
        if (next) startNewChat();
        refreshConversations(
          false,
          next ? null : selectedFolderId,
          selectedWorkspaceId,
          next ? null : selectedProjectId,
          conversationSearch,
          next
        );
      },
    },
    {
      id: "files",
      label: t("commandPalette.actions.files"),
      keywords: ["files", "pdf", "ملفات"],
      icon: "📎",
      onSelect: () => setShowFiles(true),
    },
    {
      id: "account",
      label: t("commandPalette.actions.account"),
      keywords: ["account", "profile", "حساب"],
      icon: "👤",
      onSelect: () => setShowAccountSettings(true),
    },
    {
      id: "billing",
      label: t("commandPalette.actions.billing"),
      keywords: ["billing", "subscription", "اشتراك"],
      icon: "💳",
      onSelect: () => setShowBilling(true),
    },
    {
      id: "new-folder",
      label: t("commandPalette.actions.newFolder"),
      keywords: ["folder", "folders", "مجلد"],
      icon: "📁",
      onSelect: handleCreateFolder,
    },
    {
      id: "new-project",
      label: t("commandPalette.actions.newProject"),
      keywords: ["project", "projects", "مشروع"],
      icon: "🗂",
      onSelect: handleCreateProject,
    },
    {
      id: "new-assistant",
      label: t("commandPalette.actions.newAssistant"),
      keywords: ["assistant", "مساعد"],
      icon: "🤖",
      onSelect: openCreateAssistantEditor,
    },
    {
      id: "scheduled-tasks",
      label: t("commandPalette.actions.scheduledTasks"),
      keywords: ["schedule", "task", "مهام", "مجدولة"],
      icon: "⏰",
      onSelect: () => setShowScheduledTasks(true),
    },
    ...(currentUserRole === "admin"
      ? [{
          id: "admin",
          label: t("commandPalette.actions.admin"),
          keywords: ["admin", "dashboard", "إدارة"],
          icon: "⚙",
          onSelect: () => setShowAdmin(true),
        }]
      : []),
  ];
}
