import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { FixedSizeList } from "react-window";
import AutoSizer from "react-virtualized-auto-sizer";

const ROW_HEIGHT = 68;
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
  onToggleArchiveConversation,
  showArchived,
  onShowArchived,
  loading,
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const filteredConversations = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    if (!query) return conversations;
    return conversations.filter((item) =>
      (item.title || "").toLocaleLowerCase().includes(query)
    );
  }, [conversations, search]);

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
          onSelectConversation(item.id);
          setOpen(false);
        }}
        className="group h-full cursor-pointer rounded-xl border border-slate-200 px-3 py-3 hover:bg-slate-50"
      >
        <div className="flex items-center justify-between gap-2">
          <span className="flex min-w-0 items-center gap-1 truncate font-medium">{item.is_pinned ? <span aria-hidden="true">★</span> : null}<span className="truncate">{item.title}</span></span>
          <div className="flex shrink-0 items-center gap-1">
            <span className="text-xs text-slate-400">
              {new Date(item.created_at).toLocaleDateString()}
            </span>
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
              onClick={(e) => handleRename(e, item)}
              title={t("sidebar.renameTitle")}
              className="rounded-lg px-1.5 py-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400"
            >
              ✎
            </button>
            <button
              onClick={(e) => handleDelete(e, item)}
              title={t("sidebar.deleteTitle")}
              className="rounded-lg px-1.5 py-0.5 text-slate-400 hover:bg-red-100 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-slate-400"
            >
              ✕
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
        className={`fixed inset-y-0 start-0 z-40 w-80 border-e border-slate-200 bg-white transition-transform dark:border-slate-700 dark:bg-slate-900 md:static md:flex md:flex-col ${
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
          <button
            onClick={() => {
              onNewChat();
              setOpen(false);
            }}
            className="mt-3 w-full rounded-xl bg-slate-900 px-4 py-2 text-white hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1"
          >
            {t("newChat")}
          </button>
          <button type="button" onClick={() => onShowArchived(!showArchived)} className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">{showArchived ? t("sidebar.backToChats") : t("sidebar.archivedTitle")}</button>
          <label className="mt-3 block">
            <span className="sr-only">
              {document.documentElement.lang === "ar" ? "البحث في المحادثات" : "Search conversations"}
            </span>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={
                document.documentElement.lang === "ar"
                  ? "ابحث في المحادثات..."
                  : "Search conversations..."
              }
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
            />
          </label>
        </div>

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
      </aside>
    </>
  );
}
