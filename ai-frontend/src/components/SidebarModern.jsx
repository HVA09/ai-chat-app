import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAppDialog } from "./AppDialog";
import WorkspaceSharedConversationsPanel from "./WorkspaceSharedConversationsPanel";
import Icon from "./ui/Icon";

function Section({ title, icon, open, onToggle, children, action }) {
  return (
    <section className="modern-sidebar-section">
      <div className="modern-sidebar-section-title">
        <button type="button" onClick={onToggle} className="modern-sidebar-section-toggle">
          <Icon name={icon} size={15} />
          <span>{title}</span>
          <Icon name={open ? "chevronDown" : "chevronRight"} size={14} className="ms-auto opacity-55" />
        </button>
        {action}
      </div>
      {open ? <div className="modern-sidebar-section-body">{children}</div> : null}
    </section>
  );
}

export default function SidebarModern({
  conversations,
  selectedConversationId = null,
  onSelectConversation,
  onNewChat,
  onImportConversation = () => {},
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
  folders = [],
  selectedFolderId = null,
  onSelectFolder = () => {},
  onCreateFolder = () => {},
  onRenameFolder = () => {},
  onDeleteFolder = () => {},
  onMoveFolder = () => {},
  projects = [],
  selectedProjectId = null,
  onSelectProject = () => {},
  onCreateProject = () => {},
  onRenameProject = () => {},
  onDeleteProject = () => {},
  tags = [],
  selectedTagId = null,
  onSelectTag = () => {},
  onCreateTag = () => {},
  onRenameTag = () => {},
  onDeleteTag = () => {},
  selectedConversationIds = [],
  onToggleConversationSelection = () => {},
  onToggleSelectAllVisible = () => {},
  onClearSelectedConversations = () => {},
  onBulkArchive = () => {},
  onBulkDelete = () => {},
  onBulkExport = () => {},
  onBulkMoveToFolder = () => {},
  workspaces = [],
  selectedWorkspaceId = null,
  selectedWorkspaceRole = "member",
  onSelectWorkspace = () => {},
  onCreateWorkspace = () => {},
  onRenameWorkspace = () => {},
  onOpenWorkspaceMembers = () => {},
  onOpenScheduledTasks = () => {},
  onOpenWorkspaceSharedConversation = () => {},
  onDuplicatedWorkspaceConversation = () => {},
  showArchived = false,
  onShowArchived = () => {},
  onShowTrash = () => {},
  searchValue = "",
  onSearchChange = () => {},
  loading = false,
  loadingMore = false,
  hasMore = false,
  onLoadMore = () => {},
}) {
  const { t } = useTranslation();
  const { prompt } = useAppDialog();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [libraryOpen, setLibraryOpen] = useState(true);
  const [openSection, setOpenSection] = useState(null);
  const [contextOpenId, setContextOpenId] = useState(null);
  const importRef = useRef(null);

  useEffect(() => {
    const handleOpen = () => setMobileOpen(true);
    const handleClose = () => setMobileOpen(false);
    window.addEventListener("app:open-sidebar", handleOpen);
    window.addEventListener("app:close-sidebar", handleClose);
    return () => {
      window.removeEventListener("app:open-sidebar", handleOpen);
      window.removeEventListener("app:close-sidebar", handleClose);
    };
  }, []);

  const recent = conversations || [];
  const allSelected = recent.length > 0 && recent.every((item) => selectedConversationIds.includes(item.id));

  const formatConversationMeta = (item) => {
    const value = item.updated_at ?? item.created_at;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    const now = new Date();
    const sameDay = now.toDateString() === date.toDateString();
    return sameDay
      ? date.toLocaleTimeString(document.documentElement.lang === "ar" ? "ar-LY" : "en-US", { hour: "numeric", minute: "2-digit" })
      : date.toLocaleDateString(document.documentElement.lang === "ar" ? "ar-LY" : "en-US", { month: "short", day: "numeric" });
  };

  const closeMobile = () => setMobileOpen(false);

  const selectConversation = async (id) => {
    closeMobile();
    setContextOpenId(null);
    await onSelectConversation(id);
  };

  const toggleSection = (name) => setOpenSection((current) => (current === name ? null : name));

  const sidebarTitle = showTrash
    ? t("sidebar.trashTitle")
    : showArchived
      ? t("sidebar.archivedTitle")
      : t("appName");

  const visibleAssistants = useMemo(() => assistants, [assistants]);
  const visibleProjects = useMemo(() => projects, [projects]);
  const visibleFolders = useMemo(() => folders, [folders]);
  const visibleTags = useMemo(() => tags, [tags]);

  const handleSelectAll = () => onToggleSelectAllVisible(recent.map((item) => item.id));

  return (
    <>
      {mobileOpen ? (
        <button
          type="button"
          aria-label="Close sidebar"
          onClick={() => setMobileOpen(false)}
          className="modern-sidebar-backdrop md:hidden"
        />
      ) : null}

      <aside className={`modern-sidebar ${mobileOpen ? "modern-sidebar-open" : ""}`}>
        <div className="modern-sidebar-top">
          <div className="modern-brand-row">
            <div className="modern-brand-mark">AI</div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">{t("appName")}</p>
              <p className="truncate text-[11px] text-slate-400">{sidebarTitle}</p>
            </div>
            <button type="button" onClick={() => setMobileOpen(false)} className="modern-icon-button md:hidden" aria-label="Close navigation">
              <Icon name="close" size={17} />
            </button>
          </div>

          <div className="modern-workspace-row">
            <select
              aria-label={t("sidebar.workspaceSelectTitle")}
              value={selectedWorkspaceId ?? ""}
              onChange={(e) => onSelectWorkspace(e.target.value)}
              className="modern-workspace-select"
            >
              {workspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
              ))}
            </select>
            <button type="button" onClick={onCreateWorkspace} className="modern-icon-button" title={t("sidebar.workspaceCreateTitle")}><Icon name="plus" size={17} /></button>
          </div>

          <button type="button" onClick={() => { onNewChat(); setMobileOpen(false); }} className="modern-new-chat">
            <Icon name="plus" size={18} />
            <span>{t("newChat")}</span>
            <span className="ms-auto modern-shortcut">Ctrl K</span>
          </button>

          <label className="modern-search">
            <Icon name="search" size={16} />
            <input
              value={searchValue}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder={document.documentElement.lang === "ar" ? "البحث في المحادثات..." : "Search conversations..."}
              aria-label={document.documentElement.lang === "ar" ? "البحث في المحادثات" : "Search conversations"}
            />
            <span className="modern-search-key">⌘K</span>
          </label>

          <div className="modern-quick-row">
            <button type="button" onClick={() => onShowArchived(!showArchived)} className={`modern-quick-button ${showArchived ? "active" : ""}`}>
              <Icon name="archive" size={15} />{showArchived ? t("sidebar.backToChats") : t("sidebar.archivedTitle")}
            </button>
            <button type="button" onClick={() => onShowTrash(!showTrash)} className={`modern-quick-button ${showTrash ? "active danger" : ""}`}>
              <Icon name="trash" size={15} />{showTrash ? t("sidebar.backToChats") : t("sidebar.trashTitle")}
            </button>
          </div>
        </div>

        <div className="modern-conversation-panel">
          <div className="modern-panel-heading">
            <span>{document.documentElement.lang === "ar" ? "المحادثات الأخيرة" : "Recent chats"}</span>
            <span className="modern-count">{recent.length}</span>
          </div>

          {loading ? (
            <div className="space-y-2 p-2">
              {[1, 2, 3].map((item) => <div key={item} className="modern-skeleton h-14 rounded-xl" />)}
            </div>
          ) : recent.length === 0 ? (
            <div className="modern-empty-sidebar">
              <div className="modern-empty-icon"><Icon name="chat" size={20} /></div>
              <p>{searchValue.trim() ? (document.documentElement.lang === "ar" ? "لا توجد نتائج" : "No matches") : t("noChats")}</p>
              <button type="button" onClick={onNewChat}>{t("newChat")}</button>
            </div>
          ) : (
            <div className="modern-conversation-scroll">
              {recent.map((item) => {
                const active = Number(item.id) === Number(selectedConversationId);
                return (
                  <div key={item.id} className={`modern-conversation-item ${active ? "active" : ""}`}>
                    <button
                      type="button"
                      onClick={() => selectConversation(item.id)}
                      className="modern-conversation-main"
                      aria-current={active ? "page" : undefined}
                    >
                      <span className="modern-chat-dot"><Icon name="chat" size={14} /></span>
                      <span className="min-w-0 flex-1 text-start">
                        <span className="block truncate text-sm font-medium">{item.title}</span>
                        <span className="block truncate text-[11px] text-slate-400">{formatConversationMeta(item)}</span>
                      </span>
                      {item.is_pinned ? <span className="text-amber-500">★</span> : null}
                    </button>
                    <div className="modern-row-tools">
                      <input
                        type="checkbox"
                        aria-label={t("sidebar.selectConversation", { title: item.title })}
                        checked={selectedConversationIds.includes(item.id)}
                        onChange={(event) => {
                          event.stopPropagation();
                          onToggleConversationSelection(item.id);
                        }}
                        onClick={(event) => event.stopPropagation()}
                        className="h-3.5 w-3.5 rounded border-slate-300"
                      />
                      <button
                        type="button"
                        className="modern-conversation-more"
                        title={t("sidebar.renameTitle")}
                        onClick={(event) => {
                          event.stopPropagation();
                          setContextOpenId((current) => current === item.id ? null : item.id);
                        }}
                      >
                        <Icon name="more" size={16} />
                      </button>
                    </div>
                    {contextOpenId === item.id ? (
                      <div className="modern-conversation-menu">
                        <button type="button" onClick={() => { onTogglePinConversation(item.id); setContextOpenId(null); }} title={item.is_pinned ? t("sidebar.unpinTitle") : t("sidebar.pinTitle")}><Icon name="pin" size={14} /></button>
                        <button type="button" onClick={async () => { const title = await prompt({ title: t("sidebar.renamePrompt"), message: t("sidebar.renamePrompt"), defaultValue: item.title }); if (title?.trim()) onRenameConversation(item.id, title.trim()); setContextOpenId(null); }} title={t("sidebar.renameTitle")}><Icon name="edit" size={14} /></button>
                        <button type="button" onClick={() => { onDuplicateConversation(item.id); setContextOpenId(null); }} title={t("sidebar.duplicateTitle")}><Icon name="copy" size={14} /></button>
                        <button type="button" onClick={() => { onToggleArchiveConversation(item.id); setContextOpenId(null); }} title={showArchived ? t("sidebar.unarchiveTitle") : t("sidebar.archiveTitle")}><Icon name="archive" size={14} /></button>
                        <button type="button" onClick={() => { onToggleTrashConversation(item.id); setContextOpenId(null); }} title={t("sidebar.trashTitle")}><Icon name="trash" size={14} /></button>
                      </div>
                    ) : null}
                  </div>
                );
              })}
              {hasMore ? (
                <button type="button" className="modern-load-more" onClick={onLoadMore} disabled={loadingMore}>
                  {loadingMore ? t("sidebar.loadingMore") : t("sidebar.loadMore")}
                </button>
              ) : null}
            </div>
          )}
        </div>

        <div className="modern-library">
          <button type="button" onClick={() => setLibraryOpen((value) => !value)} className="modern-library-toggle">
            <span className="flex items-center gap-2"><Icon name="folder" size={15} />{document.documentElement.lang === "ar" ? "المكتبة" : "Library"}</span>
            <Icon name={libraryOpen ? "chevronDown" : "chevronRight"} size={15} />
          </button>

          {libraryOpen ? (
            <div className="modern-library-scroll">
              <Section title={t("sidebar.projectsTitle")} icon="project" open={openSection === "projects"} onToggle={() => toggleSection("projects")} action={<button type="button" className="modern-section-add" onClick={onCreateProject}>+</button>}>
                <button type="button" onClick={() => { closeMobile(); onSelectProject(null); }} className={`modern-library-item ${selectedProjectId === null ? "active" : ""}`}><Icon name="project" size={14} /><span>{t("sidebar.allProjects")}</span></button>
                {visibleProjects.map((project) => (
                  <div key={project.id} className="modern-library-item-group">
                    <button type="button" onClick={() => onSelectProject(project.id)} className={`modern-library-item ${selectedProjectId === project.id ? "active" : ""}`}><Icon name="project" size={14} /><span className="truncate">{project.name}</span></button>
                    {(selectedWorkspaceRole === "owner" || selectedWorkspaceRole === "admin") ? (
                      <button type="button" className="modern-item-action" onClick={() => onRenameProject(project.id)} title={t("sidebar.renameProjectTitle")}><Icon name="edit" size={13} /></button>
                    ) : null}
                  </div>
                ))}
              </Section>

              <Section title={t("sidebar.foldersTitle")} icon="folder" open={openSection === "folders"} onToggle={() => toggleSection("folders")} action={<button type="button" className="modern-section-add" onClick={onCreateFolder}>+</button>}>
                <button type="button" onClick={() => { closeMobile(); onSelectFolder(null); }} className={`modern-library-item ${selectedFolderId === null ? "active" : ""}`}><Icon name="folder" size={14} /><span>{t("sidebar.allConversations")}</span></button>
                {visibleFolders.map((folder) => (
                  <div key={folder.id} className="modern-library-item-group">
                    <button type="button" onClick={() => onSelectFolder(folder.id)} className={`modern-library-item ${selectedFolderId === folder.id ? "active" : ""}`}><span className={`h-2.5 w-2.5 rounded-full bg-slate-400`} /><span className="truncate">{folder.name}</span></button>
                    <div className="flex items-center">
                      <button type="button" className="modern-item-action" onClick={() => onRenameFolder(folder.id, folder.name, folder.color ?? "slate")} title={t("sidebar.renameFolderTitle")}><Icon name="edit" size={13} /></button>
                      <button type="button" className="modern-item-action danger" onClick={() => onDeleteFolder(folder.id)} title={t("sidebar.deleteFolderTitle")}><Icon name="trash" size={13} /></button>
                    </div>
                  </div>
                ))}
              </Section>

              <Section title={t("sidebar.assistantsTitle")} icon="robot" open={openSection === "assistants"} onToggle={() => toggleSection("assistants")} action={<button type="button" className="modern-section-add" onClick={onCreateAssistant}>+</button>}>
                <button type="button" onClick={() => { closeMobile(); onSelectAssistant(null); }} className={`modern-library-item ${selectedAssistantId === null ? "active" : ""}`}><Icon name="robot" size={14} /><span>{t("sidebar.defaultAssistant")}</span></button>
                {visibleAssistants.map((assistant) => (
                  <div key={assistant.id} className="modern-library-item-group">
                    <button type="button" onClick={() => onSelectAssistant(assistant.id)} className={`modern-library-item ${selectedAssistantId === assistant.id ? "active" : ""}`}><Icon name="robot" size={14} /><span className="truncate">{assistant.name}</span></button>
                    {assistant.can_edit !== false ? (
                      <div className="flex items-center">
                        <button type="button" className="modern-item-action" onClick={() => onEditAssistant(assistant.id)} title={t("sidebar.editAssistantTitle")}><Icon name="edit" size={13} /></button>
                        <button type="button" className="modern-item-action danger" onClick={() => onDeleteAssistant(assistant.id, assistant.name)} title={t("sidebar.deleteAssistantTitle")}><Icon name="trash" size={13} /></button>
                      </div>
                    ) : null}
                  </div>
                ))}
              </Section>

              <Section title={t("sidebar.tagsTitle")} icon="tag" open={openSection === "tags"} onToggle={() => toggleSection("tags")} action={<button type="button" className="modern-section-add" onClick={onCreateTag}>+</button>}>
                <button type="button" onClick={() => { closeMobile(); onSelectTag(null); }} className={`modern-library-item ${selectedTagId === null ? "active" : ""}`}><Icon name="tag" size={14} /><span>{t("sidebar.allTags")}</span></button>
                {visibleTags.map((tag) => (
                  <div key={tag.id} className="modern-library-item-group">
                    <button type="button" onClick={() => onSelectTag(tag.id)} className={`modern-library-item ${selectedTagId === tag.id ? "active" : ""}`}><span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: tag.color }} /><span className="truncate">{tag.name}</span></button>
                    <div className="flex items-center">
                      <button type="button" className="modern-item-action" onClick={() => onRenameTag(tag.id, tag.name, tag.color)} title={t("sidebar.renameTagTitle")}><Icon name="edit" size={13} /></button>
                      <button type="button" className="modern-item-action danger" onClick={() => onDeleteTag(tag.id, tag.name)} title={t("sidebar.deleteTagTitle")}><Icon name="trash" size={13} /></button>
                    </div>
                  </div>
                ))}
              </Section>

              <Section title={t("bookmarks.title")} icon="bookmark" open={openSection === "bookmarks"} onToggle={() => toggleSection("bookmarks")}>
                {bookmarkedMessages.length ? bookmarkedMessages.slice(0, 8).map((item) => (
                  <button key={item.message_id} type="button" onClick={() => onOpenBookmarkedMessage(item)} className="modern-library-item block text-start">
                    <Icon name="bookmark" size={14} /><span className="min-w-0 truncate">{item.conversation_title}</span>
                  </button>
                )) : <p className="px-2 py-2 text-xs text-slate-400">{t("bookmarks.empty")}</p>}
              </Section>

              <Section title={t("sidebar.savedPromptsTitle")} icon="edit" open={openSection === "prompts"} onToggle={() => toggleSection("prompts")} action={<button type="button" className="modern-section-add" onClick={onCreateSavedPrompt}>+</button>}>
                {savedPrompts.map((prompt) => (
                  <div key={prompt.id} className="modern-library-item-group">
                    <button type="button" onClick={() => onUseSavedPrompt(prompt.content)} className="modern-library-item"><Icon name="edit" size={14} /><span className="truncate">{prompt.name}</span></button>
                    <button type="button" className="modern-item-action" onClick={() => onRenameSavedPrompt(prompt.id, prompt.name, prompt.content)} title={t("sidebar.editSavedPromptTitle")}><Icon name="edit" size={13} /></button>
                  </div>
                ))}
              </Section>

              <Section title={document.documentElement.lang === "ar" ? "إدارة مساحة العمل" : "Workspace"} icon="settings" open={openSection === "workspace"} onToggle={() => toggleSection("workspace")}>
                <div className="grid grid-cols-2 gap-2">
                  <button type="button" className="modern-library-tile" onClick={onRenameWorkspace}><Icon name="edit" size={14} />{t("sidebar.workspaceRenameTitle")}</button>
                  <button type="button" className="modern-library-tile" onClick={onOpenWorkspaceMembers}><Icon name="settings" size={14} />{t("sidebar.workspaceMembersTitle")}</button>
                  <button type="button" className="modern-library-tile" onClick={onOpenScheduledTasks}><Icon name="settings" size={14} />{t("sidebar.scheduledTasksTitle")}</button>
                  <label className="modern-library-tile cursor-pointer"><Icon name="copy" size={14} />{t("sidebar.importConversation")}
                    <input ref={importRef} type="file" accept=".json,application/json" className="hidden" onChange={(event) => { const file = event.target.files?.[0]; event.target.value = ""; if (file) onImportConversation(file); }} />
                  </label>
                </div>
              </Section>

              {selectedConversationIds.length ? (
                <div className="modern-bulk-bar">
                  <button type="button" onClick={onBulkArchive}>{showArchived ? t("sidebar.bulkUnarchive") : t("sidebar.bulkArchive")}</button>
                  <button type="button" onClick={onBulkExport}>{t("sidebar.bulkExport")}</button>
                  <button type="button" onClick={onBulkDelete}>{showTrash ? t("sidebar.bulkDelete") : t("sidebar.bulkTrash")}</button>
                  <select defaultValue="" onChange={(event) => { onBulkMoveToFolder(event.target.value); event.target.value = ""; }}><option value="">{t("sidebar.bulkMoveTitle")}</option>{folders.map((folder) => <option key={folder.id} value={folder.id}>{folder.name}</option>)}</select>
                  <button type="button" onClick={onClearSelectedConversations}>{t("sidebar.clearSelection")}</button>
                </div>
              ) : null}

              <label className="modern-select-all">
                <input type="checkbox" checked={allSelected} disabled={!recent.length} onChange={handleSelectAll} />
                <span>{t("sidebar.selectAllVisible")}</span>
              </label>
            </div>
          ) : null}
        </div>

        <div className="modern-sidebar-footer">
          <WorkspaceSharedConversationsPanel
            workspaceId={selectedWorkspaceId}
            onOpenConversation={onOpenWorkspaceSharedConversation}
            onDuplicatedConversation={onDuplicatedWorkspaceConversation}
          />
        </div>
      </aside>
    </>
  );
}
