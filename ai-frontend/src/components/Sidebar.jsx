import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { FixedSizeList } from "react-window";
import AutoSizer from "react-virtualized-auto-sizer";
import WorkspaceSharedConversationsPanel from "./WorkspaceSharedConversationsPanel";

const ROW_HEIGHT = 92;
// نفعّل الفرز الافتراضي (بدون virtualization) لقوائم صغيرة — أبسط وكافي.
// الـ virtualization يفيد فعليًا لما تكبر القائمة (مستخدم عنده مئات المحادثات)
const VIRTUALIZE_THRESHOLD = 30;

export default function Sidebar({
  conversations,
  onSelectConversation,
  onNewChat,
  onRenameConversation,
  onDeleteConversation,
  onTogglePinConversation,
  onDuplicateConversation = () => {},
  onToggleArchiveConversation,
  onToggleTrashConversation = () => {},
  showTrash = false,
  assistants = [],
  selectedAssistantId = null,
  onSelectAssistant = () => {},
  onCreateAssistant = () => {},
  onEditAssistant = () => {},
  onDeleteAssistant = () => {},
  onToggleShareAssistant = () => {},
  bookmarkedMessages = [],
  onOpenBookmarkedMessage = () => {},
  savedPrompts = [],
  onCreateSavedPrompt = () => {},
  onRenameSavedPrompt = () => {},
  onDeleteSavedPrompt = () => {},
  onUseSavedPrompt = () => {},
  folders,
  selectedFolderId,
  onSelectFolder,
  projects = [],
  selectedProjectId = null,
  onSelectProject = () => {},
  onCreateProject = () => {},
  onRenameProject = () => {},
  onDeleteProject = () => {},
  onMoveConversationToProject = () => {},
  tags = [],
  selectedTagId = null,
  onSelectTag = () => {},
  onCreateTag = () => {},
  onRenameTag = () => {},
  onDeleteTag = () => {},
  onSetConversationTags = () => {},
  onCreateFolder,
  onRenameFolder,
  onDeleteFolder,
  onMoveConversationToFolder,
  selectedConversationIds = [],
  onToggleConversationSelection = () => {},
  searchValue = "",
  onSearchChange = () => {},
  onToggleSelectAllVisible = () => {},
  onClearSelectedConversations = () => {},
  onBulkArchive = () => {},
  onBulkDelete = () => {},
  onBulkMoveToFolder = () => {},
  workspaces = [],
  selectedWorkspaceId = null,
  selectedWorkspaceRole = "member",
  onSelectWorkspace = () => {},
  onCreateWorkspace = () => {},
  onRenameWorkspace = () => {},
  onOpenWorkspaceMembers = () => {},
  onOpenWorkspaceSharedConversation = () => {},
  showArchived,
  onShowArchived,
  onShowTrash = () => {},
  loading,
  loadingMore = false,
  hasMore = false,
  onLoadMore = () => {},
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState(searchValue);
  const [tagPickerConversationId, setTagPickerConversationId] = useState(null);

  useEffect(() => {
    setSearch(searchValue);
  }, [searchValue]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      onSearchChange(search);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [search, onSearchChange]);

  const filteredConversations = conversations;

  const filteredConversationIds = useMemo(
    () => filteredConversations.map((item) => item.id),
    [filteredConversations]
  );

  const allVisibleSelected =
    filteredConversationIds.length > 0 &&
    filteredConversationIds.every((id) => selectedConversationIds.includes(id));

  const handleRename = (e, item) => {
    e.stopPropagation();
    const newTitle = window.prompt(t("sidebar.renamePrompt"), item.title);
    if (newTitle && newTitle.trim() && newTitle.trim() !== item.title) {
      onRenameConversation(item.id, newTitle.trim());
    }
  };

  const handleTogglePin = (e, item) => {
    e.stopPropagation();
    onTogglePinConversation(item.id);
  };

  const handleToggleArchive = (e, item) => {
    e.stopPropagation();
    onToggleArchiveConversation(item.id);
  };

  const handleToggleTrash = (e, item) => {
    e.stopPropagation();
    if (showTrash) {
      const confirmed = window.confirm(
        t("sidebar.permanentDeleteConfirm", { title: item.title })
      );
      if (confirmed) onDeleteConversation(item.id);
      return;
    }
    onToggleTrashConversation(item.id);
  };

  const handleToggleConversationTag = (e, item, tagId) => {
    e.stopPropagation();
    const current = new Set((item.tags || []).map((tag) => tag.id));
    if (current.has(tagId)) current.delete(tagId);
    else current.add(tagId);
    onSetConversationTags(item.id, Array.from(current));
  };

  const handleMoveFolder = (e, item) => {
    e.stopPropagation();
    onMoveConversationToFolder(item.id, e.target.value);
  };

  const handleMoveProject = (e, item) => {
    e.stopPropagation();
    onMoveConversationToProject(item.id, e.target.value);
  };

  const handleRenameProject = (e, project) => {
    e.stopPropagation();
    onRenameProject(project.id, project.name, project.description);
  };

  const handleDeleteProject = (e, project) => {
    e.stopPropagation();
    onDeleteProject(project.id, project.name);
  };

  const handleRenameFolder = (e, folder) => {
    e.stopPropagation();
    const newName = window.prompt(t("sidebar.folderRenamePrompt"), folder.name);
    if (newName && newName.trim() && newName.trim() !== folder.name) {
      onRenameFolder(folder.id, newName.trim());
    }
  };

  const handleOpenBookmarkedMessage = async (e, item) => {
    e.stopPropagation();
    await onOpenBookmarkedMessage(item);
    setOpen(false);
  };

  const handleRenameSavedPrompt = (e, prompt) => {
    e.stopPropagation();
    onRenameSavedPrompt(prompt.id, prompt.name, prompt.content);
  };

  const handleDeleteSavedPrompt = (e, prompt) => {
    e.stopPropagation();
    onDeleteSavedPrompt(prompt.id, prompt.name);
  };

  const handleUseSavedPrompt = (e, prompt) => {
    e.stopPropagation();
    onUseSavedPrompt(prompt.content);
    setOpen(false);
  };

  const handleDeleteFolder = (e, folder) => {
    e.stopPropagation();
    if (window.confirm(t("sidebar.folderDeleteConfirm", { name: folder.name }))) {
      onDeleteFolder(folder.id);
    }
  };

  const handleSelectConversationCheckbox = (e, item) => {
    e.stopPropagation();
    onToggleConversationSelection(item.id);
  };

  const handleDelete = (e, item) => {
    e.stopPropagation();
    if (window.confirm(t("sidebar.confirmDelete", { title: item.title }))) {
      onDeleteConversation(item.id);
    }
  };

  const ConversationRow = ({ item, style }) => (
    <div style={style} className="px-4">
      <div
        onClick={() => {
          if (showTrash) return;
          onSelectConversation(item.id);
          setOpen(false);
        }}
        className="group relative h-full cursor-pointer rounded-xl border border-slate-200 px-3 py-3 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
      >
        <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <span className="flex min-w-0 items-center gap-2 truncate font-medium">
            <input
              type="checkbox"
              aria-label={t("sidebar.selectConversation", { title: item.title })}
              checked={selectedConversationIds.includes(item.id)}
              onChange={(e) => handleSelectConversationCheckbox(e, item)}
              onClick={(e) => e.stopPropagation()}
              className="h-4 w-4 shrink-0 rounded border-slate-300 text-slate-900 focus:ring-slate-500"
            />{item.is_pinned ? <span aria-hidden="true">★</span> : null}<span className="truncate">{item.title}</span></span>
          <div className="flex flex-wrap items-center justify-end gap-1">
            <span className="hidden text-xs text-slate-400 sm:inline">{new Date(item.updated_at ?? item.created_at).toLocaleDateString()}</span>
{!showTrash && (
              <>
                            <button
                              onClick={(e) => handleTogglePin(e, item)}
                              title={item.is_pinned ? t("sidebar.unpinTitle") : t("sidebar.pinTitle")}
                              className="rounded-lg px-1.5 py-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400"
                            >
                              {item.is_pinned ? "★" : "☆"}
                            </button>
                            <button
                              onClick={(e) => handleToggleArchive(e, item)}
                              title={showArchived ? t("sidebar.unarchiveTitle") : t("sidebar.archiveTitle")}
                              className="rounded-lg px-1.5 py-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400"
                            >
                              {showArchived ? "↩" : "▱"}
                            </button>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                onDuplicateConversation(item.id);
                              }}
                              title={t("sidebar.duplicateTitle")}
                              className="rounded-lg px-1.5 py-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400"
                            >
                              ⧉
                            </button>
                            <button
                              onClick={(e) => handleRename(e, item)}
                              title={t("sidebar.renameTitle")}
                              className="rounded-lg px-1.5 py-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400"
                            >
                              ✎
                            </button>
                            <select
                              aria-label={t("sidebar.moveFolderTitle")}
                              value={item.folder_id ?? ""}
                              onChange={(e) => handleMoveFolder(e, item)}
                              onClick={(e) => e.stopPropagation()}
                              className="min-w-[110px] max-w-full rounded-lg border border-slate-200 bg-white px-1.5 py-1 text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 sm:max-w-[140px]"
                            >
                              <option value="">{t("sidebar.noFolder")}</option>
                              {folders.map((folder) => (
                                <option key={folder.id} value={folder.id}>{folder.name}</option>
                              ))}
                            </select>
                            <select
                              aria-label={t("sidebar.moveProjectTitle")}
                              value={item.project_id ?? ""}
                              onChange={(e) => handleMoveProject(e, item)}
                              onClick={(e) => e.stopPropagation()}
                              className="min-w-[110px] max-w-full rounded-lg border border-slate-200 bg-white px-1.5 py-1 text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 sm:max-w-[140px]"
                            >
                              <option value="">{t("sidebar.noProject")}</option>
                              {projects.map((project) => (
                                <option key={project.id} value={project.id}>{project.name}</option>
                              ))}
                            </select>
                            <button
                              type="button"
                              title={t("sidebar.tagConversationTitle")}
                              onClick={(e) => {
                                e.stopPropagation();
                                setTagPickerConversationId((current) =>
                                  current === item.id ? null : item.id
                                );
                              }}
                              className="rounded-lg px-1.5 py-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400"
                            >
                              🏷
                            </button>
                
              </>
            )}
            {!showTrash && tagPickerConversationId === item.id && (
              <div
                className="absolute end-3 top-12 z-50 w-56 rounded-xl border border-slate-200 bg-white p-2 shadow-lg dark:border-slate-700 dark:bg-slate-900"
                onClick={(e) => e.stopPropagation()}
              >
                <p className="mb-2 text-xs font-semibold text-slate-500 dark:text-slate-400">
                  {t("sidebar.tagPickerTitle")}
                </p>
                {tags.length === 0 ? (
                  <p className="text-xs text-slate-400">{t("sidebar.noTags")}</p>
                ) : (
                  <div className="max-h-48 space-y-1 overflow-y-auto">
                    {tags.map((tag) => {
                      const checked = (item.tags || []).some((itemTag) => itemTag.id === tag.id);
                      return (
                        <label key={tag.id} className="flex items-center gap-2 rounded-lg px-2 py-1 hover:bg-slate-50 dark:hover:bg-slate-800">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={(e) => handleToggleConversationTag(e, item, tag.id)}
                            className="h-4 w-4 rounded border-slate-300"
                          />
                          <span
                            className="h-2.5 w-2.5 rounded-full"
                            style={{ backgroundColor: tag.color }}
                            aria-hidden="true"
                          />
                          <span className="min-w-0 flex-1 truncate text-xs text-slate-600 dark:text-slate-300">
                            {tag.name}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
            <button
              onClick={(e) => handleToggleTrash(e, item)}
              title={showTrash ? t("sidebar.deleteTitle") : t("sidebar.trashTitle")}
              className="rounded-lg px-1.5 py-0.5 text-slate-400 hover:bg-red-100 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-slate-400"
            >
              {showTrash ? "✕" : "🗑"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <>
      <button
        className="fixed start-4 top-4 z-50 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm md:hidden"
        onClick={() => setOpen(true)}
      >
        ☰
      </button>

      <aside
        className={`fixed inset-y-0 start-0 z-40 w-[min(92vw,20rem)] border-e border-slate-200 bg-white transition-transform dark:border-slate-700 dark:bg-slate-900 md:static md:flex md:flex-col ${
          open ? "translate-x-0" : "-translate-x-full rtl:translate-x-full md:translate-x-0"
        }`}
      >
        <div className="border-b border-slate-200 p-4 dark:border-slate-700">
          <div className="flex items-center justify-between">
            <h1 className="text-lg font-semibold">{t("appName")}</h1>
            <button className="md:hidden" onClick={() => setOpen(false)}>
              ✕
            </button>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <select
              aria-label={t("sidebar.workspaceSelectTitle")}
              value={selectedWorkspaceId ?? ""}
              onChange={(e) => onSelectWorkspace(e.target.value)}
              className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            >
              {workspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
              ))}
            </select>
            <button
              type="button"
              onClick={onCreateWorkspace}
              title={t("sidebar.workspaceCreateTitle")}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-500 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              +
            </button>
            <button
              type="button"
              onClick={onRenameWorkspace}
              title={t("sidebar.workspaceRenameTitle")}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-500 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              ✎
            </button>
            <button
              type="button"
              onClick={onOpenWorkspaceMembers}
              title={t("sidebar.workspaceMembersTitle")}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-500 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              👥
            </button>
          </div>

          <WorkspaceSharedConversationsPanel
            workspaceId={selectedWorkspaceId}
            onOpenConversation={onOpenWorkspaceSharedConversation}
          />

          <button
            onClick={() => {
              onNewChat();
              setOpen(false);
            }}
            className="mt-3 w-full rounded-xl bg-slate-900 px-4 py-2 text-white hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1"
          >
            {t("newChat")}
          </button>
          <div className="mt-2 flex gap-2">
            <button type="button" onClick={() => onShowArchived(!showArchived)} className="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">{showArchived ? t("sidebar.backToChats") : t("sidebar.archivedTitle")}</button>
            <button type="button" onClick={() => onShowTrash(!showTrash)} className="rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">{showTrash ? t("sidebar.backToChats") : t("sidebar.trashTitle")}</button>
          </div>

          <div className="mt-3 rounded-xl border border-slate-200 p-2 dark:border-slate-700">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                {t("sidebar.assistantsTitle")}
              </span>
              <button
                type="button"
                onClick={onCreateAssistant}
                title={t("sidebar.createAssistantTitle")}
                className="rounded-lg px-2 py-1 text-sm text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800"
              >
                +
              </button>
            </div>
            <div className="space-y-1">
              <button
                type="button"
                onClick={() => onSelectAssistant(null)}
                className={`w-full rounded-lg px-2 py-1.5 text-start text-sm ${selectedAssistantId === null ? "bg-slate-100 font-medium text-slate-900 dark:bg-slate-800 dark:text-slate-100" : "text-slate-500 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800"}`}
              >
                {t("sidebar.defaultAssistant")}
              </button>
              {assistants.map((assistant) => (
                <div key={assistant.id} className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => onSelectAssistant(assistant.id)}
                    className={`min-w-0 flex-1 truncate rounded-lg px-2 py-1.5 text-start text-sm ${selectedAssistantId === assistant.id ? "bg-slate-100 font-medium text-slate-900 dark:bg-slate-800 dark:text-slate-100" : "text-slate-500 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800"}`}
                    title={assistant.description || assistant.name}
                  >
                    🤖 {assistant.name}
                  </button>
                  {assistant.can_edit !== false && (
                    <>
                      <button
                        type="button"
                        onClick={() => onEditAssistant(assistant.id)}
                        title={t("sidebar.editAssistantTitle")}
                        className="rounded-lg px-1.5 py-1 text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                      >
                        ✎
                      </button>
                      <button
                        type="button"
                        onClick={() => onDeleteAssistant(assistant.id, assistant.name)}
                        title={t("sidebar.deleteAssistantTitle")}
                        className="rounded-lg px-1.5 py-1 text-xs text-slate-400 hover:bg-red-100 hover:text-red-600"
                      >
                        ✕
                      </button>
                    </>
                  )}
                  {assistant.can_edit !== false && selectedWorkspaceId !== null && (
                    <button
                      type="button"
                      onClick={() => onToggleShareAssistant(assistant)}
                      title={
                        assistant.is_shared
                          ? t("sidebar.unshareAssistantTitle")
                          : t("sidebar.shareAssistantTitle")
                      }
                      className="rounded-lg px-1.5 py-1 text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                    >
                      {assistant.is_shared ? "↗" : "🔗"}
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="mt-3 rounded-xl border border-slate-200 p-2 dark:border-slate-700">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">{t("sidebar.tagsTitle")}</span>
              <button
                type="button"
                onClick={onCreateTag}
                title={t("sidebar.createTagTitle")}
                className="rounded-lg px-2 py-1 text-sm text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800"
              >
                +
              </button>
            </div>
            <div className="space-y-1">
              <button
                type="button"
                onClick={() => onSelectTag(null)}
                className={`w-full rounded-lg px-2 py-1.5 text-start text-sm ${selectedTagId === null ? "bg-slate-100 font-medium text-slate-900 dark:bg-slate-800 dark:text-slate-100" : "text-slate-500 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800"}`}
              >
                {t("sidebar.allTags")}
              </button>
              {tags.map((tag) => (
                <div key={tag.id} className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => onSelectTag(tag.id)}
                    className={`min-w-0 flex-1 truncate rounded-lg px-2 py-1.5 text-start text-sm ${selectedTagId === tag.id ? "bg-slate-100 font-medium text-slate-900 dark:bg-slate-800 dark:text-slate-100" : "text-slate-500 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800"}`}
                  >
                    <span className="me-2 inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: tag.color }} aria-hidden="true" />
                    {tag.name}
                  </button>
                  <button
                    type="button"
                    onClick={() => onRenameTag(tag.id, tag.name, tag.color)}
                    title={t("sidebar.renameTagTitle")}
                    className="rounded-lg px-1.5 py-1 text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                  >
                    ✎
                  </button>
                  <button
                    type="button"
                    onClick={() => onDeleteTag(tag.id, tag.name)}
                    title={t("sidebar.deleteTagTitle")}
                    className="rounded-lg px-1.5 py-1 text-xs text-slate-400 hover:bg-red-100 hover:text-red-600"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-3 rounded-xl border border-slate-200 p-2 dark:border-slate-700">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">{t("sidebar.foldersTitle")}</span>
              <button
                type="button"
                onClick={onCreateFolder}
                title={t("sidebar.createFolderTitle")}
                className="rounded-lg px-2 py-1 text-sm text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800"
              >
                +
              </button>
            </div>
            <div className="space-y-1">
              <button
                type="button"
                onClick={() => onSelectFolder(null)}
                className={`w-full rounded-lg px-2 py-1.5 text-start text-sm ${selectedFolderId === null ? "bg-slate-100 font-medium text-slate-900 dark:bg-slate-800 dark:text-slate-100" : "text-slate-500 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800"}`}
              >
                {t("sidebar.allConversations")}
              </button>
              {folders.map((folder) => (
                <div key={folder.id} className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => onSelectFolder(folder.id)}
                    className={`min-w-0 flex-1 truncate rounded-lg px-2 py-1.5 text-start text-sm ${selectedFolderId === folder.id ? "bg-slate-100 font-medium text-slate-900 dark:bg-slate-800 dark:text-slate-100" : "text-slate-500 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800"}`}
                  >
                    📁 {folder.name}
                  </button>
                  {(!folder.workspace_id || selectedWorkspaceRole === "owner" || selectedWorkspaceRole === "admin") && (
                    <>
                      <button type="button" onClick={(e) => handleRenameFolder(e, folder)} title={t("sidebar.renameFolderTitle")} className="rounded-lg px-1.5 py-1 text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-700">✎</button>
                      <button type="button" onClick={(e) => handleDeleteFolder(e, folder)} title={t("sidebar.deleteFolderTitle")} className="rounded-lg px-1.5 py-1 text-xs text-slate-400 hover:bg-red-100 hover:text-red-600">✕</button>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="mt-3 rounded-xl border border-slate-200 p-2 dark:border-slate-700">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">{t("sidebar.projectsTitle")}</span>
              <button
                type="button"
                onClick={onCreateProject}
                title={t("sidebar.createProjectTitle")}
                className="rounded-lg px-2 py-1 text-sm text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800"
              >
                +
              </button>
            </div>
            <div className="space-y-1">
              <button
                type="button"
                onClick={() => onSelectProject(null)}
                className={`w-full rounded-lg px-2 py-1.5 text-start text-sm ${selectedProjectId === null ? "bg-slate-100 font-medium text-slate-900 dark:bg-slate-800 dark:text-slate-100" : "text-slate-500 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800"}`}
              >
                {t("sidebar.allProjects")}
              </button>
              {projects.map((project) => (
                <div key={project.id} className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => onSelectProject(project.id)}
                    className={`min-w-0 flex-1 truncate rounded-lg px-2 py-1.5 text-start text-sm ${selectedProjectId === project.id ? "bg-slate-100 font-medium text-slate-900 dark:bg-slate-800 dark:text-slate-100" : "text-slate-500 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800"}`}
                    title={project.description || project.name}
                  >
                    📦 {project.name}
                  </button>
                  {(selectedWorkspaceRole === "owner" || selectedWorkspaceRole === "admin") && (
                    <>
                      <button
                        type="button"
                        onClick={(e) => handleRenameProject(e, project)}
                        title={t("sidebar.renameProjectTitle")}
                        className="rounded-lg px-1.5 py-1 text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                      >
                        ✎
                      </button>
                      <button
                        type="button"
                        onClick={(e) => handleDeleteProject(e, project)}
                        title={t("sidebar.deleteProjectTitle")}
                        className="rounded-lg px-1.5 py-1 text-xs text-slate-400 hover:bg-red-100 hover:text-red-600"
                      >
                        ✕
                      </button>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="mt-3 rounded-xl border border-slate-200 p-2 dark:border-slate-700">
            <div className="mb-2 text-xs font-semibold text-slate-500 dark:text-slate-400">
              {t("bookmarks.title")}
            </div>
            <div className="max-h-48 space-y-1 overflow-y-auto">
              {bookmarkedMessages.length === 0 ? (
                <p className="px-2 py-1 text-xs text-slate-400">
                  {t("bookmarks.empty")}
                </p>
              ) : (
                bookmarkedMessages.map((item) => (
                  <button
                    key={item.message_id}
                    type="button"
                    onClick={(e) => handleOpenBookmarkedMessage(e, item)}
                    className="w-full rounded-lg px-2 py-1.5 text-start hover:bg-slate-50 dark:hover:bg-slate-800"
                    title={item.content}
                  >
                    <span className="block truncate text-xs font-medium text-slate-700 dark:text-slate-200">
                      ★ {item.conversation_title}
                    </span>
                    <span className="block truncate text-xs text-slate-400">
                      {item.content}
                    </span>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="mt-3 rounded-xl border border-slate-200 p-2 dark:border-slate-700">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                {t("sidebar.savedPromptsTitle")}
              </span>
              <button
                type="button"
                onClick={onCreateSavedPrompt}
                title={t("sidebar.createSavedPromptTitle")}
                className="rounded-lg px-2 py-1 text-sm text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800"
              >
                +
              </button>
            </div>
            <div className="max-h-48 space-y-1 overflow-y-auto">
              {savedPrompts.length === 0 ? (
                <p className="px-2 py-1 text-xs text-slate-400">
                  {t("sidebar.noSavedPrompts")}
                </p>
              ) : (
                savedPrompts.map((prompt) => (
                  <div key={prompt.id} className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={(e) => handleUseSavedPrompt(e, prompt)}
                      title={prompt.content}
                      className="min-w-0 flex-1 rounded-lg px-2 py-1.5 text-start hover:bg-slate-50 dark:hover:bg-slate-800"
                    >
                      <span className="block truncate text-sm font-medium text-slate-700 dark:text-slate-200">
                        📝 {prompt.name}
                      </span>
                      <span className="block truncate text-xs text-slate-400">
                        {prompt.content}
                      </span>
                    </button>
                    <button
                      type="button"
                      onClick={(e) => handleRenameSavedPrompt(e, prompt)}
                      title={t("sidebar.editSavedPromptTitle")}
                      className="rounded-lg px-1.5 py-1 text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                    >
                      ✎
                    </button>
                    <button
                      type="button"
                      onClick={(e) => handleDeleteSavedPrompt(e, prompt)}
                      title={t("sidebar.deleteSavedPromptTitle")}
                      className="rounded-lg px-1.5 py-1 text-xs text-slate-400 hover:bg-red-100 hover:text-red-600"
                    >
                      ✕
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="mt-3 flex items-center justify-between gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm dark:border-slate-700">
            <label className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
              <input
                type="checkbox"
                aria-label={t("sidebar.selectAllVisible")}
                checked={allVisibleSelected}
                disabled={filteredConversationIds.length === 0}
                onChange={() => onToggleSelectAllVisible(filteredConversationIds)}
                className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-500"
              />
              <span>{t("sidebar.selectAllVisible")}</span>
            </label>
            {selectedConversationIds.length > 0 && (
              <span className="font-medium text-slate-700 dark:text-slate-200">
                {t("sidebar.bulkSelected", { count: selectedConversationIds.length })}
              </span>
            )}
          </div>

          {selectedConversationIds.length > 0 && (
            <div className="mt-2 space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-2 dark:border-slate-700 dark:bg-slate-800">
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={onBulkArchive}
                  className="rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-white dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
                >
                  {showArchived ? t("sidebar.bulkUnarchive") : t("sidebar.bulkArchive")}
                </button>
                <button
                  type="button"
                  onClick={onBulkDelete}
                  className="rounded-lg border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                >
                  {showTrash ? t("sidebar.bulkDelete") : t("sidebar.bulkTrash")}
                </button>
                <select
                  aria-label={t("sidebar.bulkMoveTitle")}
                  defaultValue=""
                  onChange={(e) => {
                    onBulkMoveToFolder(e.target.value);
                    e.target.value = "";
                  }}
                  className="max-w-[170px] rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
                >
                  <option value="">{t("sidebar.bulkMoveTitle")}</option>
                  <option value="__none__">{t("sidebar.noFolder")}</option>
                  {folders.map((folder) => (
                    <option key={folder.id} value={folder.id}>{folder.name}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={onClearSelectedConversations}
                  className="rounded-lg px-2 py-1 text-xs text-slate-500 hover:bg-white dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  {t("sidebar.clearSelection")}
                </button>
              </div>
            </div>
          )}

          <label className="mt-3 block">
            <span className="sr-only">
              {document.documentElement.lang === "ar" ? "البحث في العناوين والرسائل" : "Search titles and messages"}
            </span>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={
                document.documentElement.lang === "ar"
                  ? "ابحث في العناوين والرسائل..."
                  : "Search titles and messages..."
              }
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
            />
          </label>
        </div>

        <div className="flex min-h-0 flex-1 flex-col">
          <div className="min-h-0 flex-1">
          {loading ? (
            <p className="px-5 py-4 text-sm text-slate-400">...</p>
          ) : filteredConversations.length === 0 ? (
            <p className="px-5 py-4 text-sm text-slate-400">
              {search.trim()
                ? document.documentElement.lang === "ar"
                  ? "لا توجد محادثات مطابقة"
                  : "No matching conversations"
                : t("noChats")}
            </p>
          ) : filteredConversations.length <= VIRTUALIZE_THRESHOLD ? (
            <div className="h-full space-y-2 overflow-y-auto p-4">
              {filteredConversations.map((item) => (
                <ConversationRow key={item.id} item={item} style={{ height: ROW_HEIGHT - 8 }} />
              ))}
            </div>
          ) : (
            <AutoSizer>
              {({ height, width }) => (
                <FixedSizeList
                  height={height}
                  width={width}
                  itemCount={filteredConversations.length}
                  itemSize={ROW_HEIGHT}
                >
                  {({ index, style }) => (
                    <ConversationRow item={filteredConversations[index]} style={style} />
                  )}
                </FixedSizeList>
              )}
            </AutoSizer>
          )}
          </div>
          {hasMore && (
            <div className="border-t border-slate-200 p-3 dark:border-slate-700">
              <button
                type="button"
                onClick={onLoadMore}
                disabled={loadingMore}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                {loadingMore ? t("sidebar.loadingMore") : t("sidebar.loadMore")}
              </button>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
