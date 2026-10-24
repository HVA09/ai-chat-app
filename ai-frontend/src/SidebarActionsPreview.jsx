import { useEffect, useMemo, useState } from "react";
import SidebarModern from "./components/SidebarModern";
import ChatHeaderModern from "./components/ChatHeaderModern";
import ChatMessage from "./components/ChatMessage";
import ChatComposer from "./components/ChatComposer";

const sampleConversations = [
  {
    id: 101,
    title: "مراجعة خطة المشروع",
    created_at: new Date().toISOString(),
    folder_id: null,
    project_id: null,
    tags: [{ id: 45, name: "مهم" }],
    is_pinned: true,
  },
  {
    id: 102,
    title: "أفكار لتطوير التطبيق",
    created_at: new Date(Date.now() - 35 * 60 * 1000).toISOString(),
    folder_id: 23,
    project_id: 34,
    tags: [],
    is_pinned: false,
  },
  {
    id: 103,
    title: "تعلم Python — الدوال",
    created_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    folder_id: 24,
    project_id: 34,
    tags: [{ id: 46, name: "تعلم" }],
    is_pinned: false,
  },
  {
    id: 104,
    title: "اختبار عرض القائمة على الهاتف",
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    folder_id: null,
    project_id: null,
    tags: [],
    is_pinned: false,
  },
  {
    id: 105,
    title: "ملاحظات العمل القادمة",
    created_at: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(),
    folder_id: null,
    project_id: null,
    tags: [],
    is_pinned: false,
  },
  {
    id: 106,
    title: "قائمة طويلة لاختبار موضع القائمة",
    created_at: new Date(Date.now() - 72 * 60 * 60 * 1000).toISOString(),
    folder_id: 23,
    project_id: null,
    tags: [],
    is_pinned: false,
  },
];

const sampleFolders = [
  { id: 23, name: "العمل" },
  { id: 24, name: "التعلّم" },
];

const sampleProjects = [
  { id: 34, name: "AI Chat App" },
  { id: 35, name: "خطة Python" },
];

const sampleTags = [
  { id: 45, name: "مهم", color: "#f59e0b" },
  { id: 46, name: "تعلم", color: "#3b82f6" },
  { id: 47, name: "للمراجعة", color: "#10b981" },
];

export default function SidebarActionsPreview() {
  const [conversations, setConversations] = useState(sampleConversations);
  const [archivedConversations, setArchivedConversations] = useState([]);
  const [trashedConversations, setTrashedConversations] = useState([]);
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [showArchived, setShowArchived] = useState(false);
  const [showTrash, setShowTrash] = useState(false);
  const [status, setStatus] = useState("هذه معاينة واجهة معزولة؛ الإجراءات تغيّر بيانات تجريبية محلية فقط.");
  const [composerValue, setComposerValue] = useState("");
  const [selectedModel, setSelectedModel] = useState("demo-fast");
  const [previewLang, setPreviewLang] = useState(document.documentElement.lang || "ar");
  const [settingsOpen, setSettingsOpen] = useState(false);

  const handlePreviewLanguageChange = (nextLang) => {
    setPreviewLang(nextLang);
    document.documentElement.lang = nextLang;
    document.documentElement.dir = nextLang === "ar" ? "rtl" : "ltr";
    setStatus("تم تغيير لغة المعاينة فقط.");
  };

  useEffect(() => {
    if (!settingsOpen) return undefined;
    const handleKeyDown = (event) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      setSettingsOpen(false);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [settingsOpen]);

  const appendCommand = (command) => {
    setComposerValue((current) => {
      const prefix = current.trim();
      return `${prefix ? `${prefix} ` : ""}/${command} `;
    });
  };

  const activeList = showTrash
    ? trashedConversations
    : showArchived
      ? archivedConversations
      : conversations;

  const updateAcrossLists = (id, updater) => {
    setConversations((items) => items.map((item) => item.id === id ? updater(item) : item));
    setArchivedConversations((items) => items.map((item) => item.id === id ? updater(item) : item));
    setTrashedConversations((items) => items.map((item) => item.id === id ? updater(item) : item));
  };

  const handleMoveToTrash = (id) => {
    const source = showArchived ? archivedConversations : conversations;
    const item = source.find((conversation) => conversation.id === id);
    if (!item) return;
    if (showArchived) {
      setArchivedConversations((items) => items.filter((conversation) => conversation.id !== id));
    } else {
      setConversations((items) => items.filter((conversation) => conversation.id !== id));
    }
    setTrashedConversations((items) => [...items, item]);
    setStatus("نُقلت المحادثة إلى سلة العرض التجريبي فقط.");
  };

  const handleArchive = (id) => {
    if (showArchived) {
      const item = archivedConversations.find((conversation) => conversation.id === id);
      if (!item) return;
      setArchivedConversations((items) => items.filter((conversation) => conversation.id !== id));
      setConversations((items) => [...items, item]);
      setStatus("أُعيدت المحادثة إلى القائمة التجريبية.");
    } else {
      const item = conversations.find((conversation) => conversation.id === id);
      if (!item) return;
      setConversations((items) => items.filter((conversation) => conversation.id !== id));
      setArchivedConversations((items) => [...items, item]);
      setStatus("أُرشفت المحادثة في بيانات العرض التجريبي.");
    }
  };

  const handleDuplicate = (id) => {
    const item = activeList.find((conversation) => conversation.id === id);
    if (!item) return;
    const nextId = Math.max(200, ...conversations.map((conversation) => conversation.id), ...archivedConversations.map((conversation) => conversation.id), ...trashedConversations.map((conversation) => conversation.id)) + 1;
    setConversations((items) => [...items, { ...item, id: nextId, title: `نسخة: ${item.title}`, is_pinned: false }]);
    setStatus("أُنشئت نسخة تجريبية محلية من المحادثة.");
  };

  const handlePermanentDelete = (id) => {
    setTrashedConversations((items) => items.filter((conversation) => conversation.id !== id));
    setStatus("حُذفت المحادثة من سلة العرض التجريبي فقط.");
  };

  const handleMoveFolder = (id, folderId) => {
    const value = folderId === "" ? null : Number(folderId);
    updateAcrossLists(id, (item) => ({ ...item, folder_id: value }));
    setStatus("تم تغيير المجلد في بيانات العرض التجريبي فقط.");
  };

  const handleMoveProject = (id, projectId) => {
    const value = projectId === "" ? null : Number(projectId);
    updateAcrossLists(id, (item) => ({ ...item, project_id: value }));
    setStatus("تم تغيير المشروع في بيانات العرض التجريبي فقط.");
  };

  const handleSetTags = (id, tagIds) => {
    const nextTags = sampleTags.filter((tag) => tagIds.includes(tag.id));
    updateAcrossLists(id, (item) => ({ ...item, tags: nextTags }));
    setStatus("تم تحديث الوسوم في بيانات العرض التجريبي فقط.");
  };

  const handleRename = (id, title) => {
    updateAcrossLists(id, (item) => ({ ...item, title }));
    setStatus("تم تغيير عنوان المحادثة محليًا في المعاينة.");
  };

  const handlePin = (id) => {
    updateAcrossLists(id, (item) => ({ ...item, is_pinned: !item.is_pinned }));
    setStatus("تم تغيير التثبيت في بيانات العرض التجريبي.");
  };

  const handleSelectTrash = (next) => {
    setShowTrash(next);
    if (next) setShowArchived(false);
  };

  const handleSelectArchived = (next) => {
    setShowArchived(next);
    if (next) setShowTrash(false);
  };

  const countLabel = useMemo(() => {
    if (showTrash) return `سلة المحذوفات التجريبية: ${activeList.length}`;
    if (showArchived) return `المحادثات المؤرشفة: ${activeList.length}`;
    return `المحادثات التجريبية: ${activeList.length}`;
  }, [activeList.length, showArchived, showTrash]);

  return (
    <div className="sidebar-preview-shell">
      <SidebarModern
        conversations={activeList}
        selectedConversationId={selectedConversationId}
        onSelectConversation={(id) => {
          setSelectedConversationId(id);
          setStatus("تم اختيار محادثة تجريبية؛ لا توجد بيانات حقيقية متصلة.");
        }}
        onNewChat={() => { setSelectedConversationId(null); setStatus("محادثة جديدة تجريبية؛ لا يتم إرسال أي طلب إلى الخادم."); }}
        onRenameConversation={handleRename}
        onDeleteConversation={handlePermanentDelete}
        onTogglePinConversation={handlePin}
        onDuplicateConversation={handleDuplicate}
        onToggleArchiveConversation={handleArchive}
        onToggleTrashConversation={handleMoveToTrash}
        onMoveConversationToFolder={handleMoveFolder}
        onMoveConversationToProject={handleMoveProject}
        onSetConversationTags={handleSetTags}
        showTrash={showTrash}
        folders={sampleFolders}
        projects={sampleProjects}
        tags={sampleTags}
        workspaces={[{ id: "", name: "مساحة تجريبية" }]}
        selectedWorkspaceId={null}
        selectedWorkspaceRole="owner"
        currentUserId={1}
        onSelectWorkspace={() => setStatus("مساحة تجريبية محلية فقط.")}
        onShowArchived={handleSelectArchived}
        onShowTrash={handleSelectTrash}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      <main className="app-main flex min-w-0 min-h-0 flex-1 flex-col">
        <ChatHeaderModern
          conversationTitle={selectedConversationId === null ? "محادثة جديدة" : (activeList.find((item) => item.id === selectedConversationId)?.title || "محادثة تجريبية")}
          lang={previewLang}
          setLang={handlePreviewLanguageChange}
          onLogout={() => setStatus("تسجيل الخروج غير متصل في المعاينة.")}
          onOpenAccount={() => setSettingsOpen(true)}
          onOpenFiles={() => setStatus("إدارة الملفات غير متصلة في المعاينة.")}
          onOpenAdmin={() => setStatus("لوحة الإدارة غير متصلة في المعاينة.")}
          onOpenBilling={() => setStatus("الفوترة غير متصلة في المعاينة.")}
          onShareConversation={() => setStatus("المشاركة غير متصلة في المعاينة.")}
          canShareConversation
          onManageShares={() => setStatus("إدارة المشاركات غير متصلة في المعاينة.")}
          canManageShares
          onToggleWorkspaceShare={() => setStatus("مشاركة مساحة العمل غير متصلة في المعاينة.")}
          canShareWithWorkspace
          workspaceShareActive={false}
          onExportConversation={() => setStatus("التصدير غير متصل في المعاينة.")}
          canExportConversation
          onSummarizeConversation={() => setStatus("التلخيص غير متصل في المعاينة.")}
          canSummarizeConversation
          onGenerateConversationTitle={() => setStatus("توليد العنوان غير متصل في المعاينة.")}
          canGenerateConversationTitle
          notifications={[]}
          onMarkNotificationRead={() => {}}
          onMarkAllNotificationsRead={() => {}}
          projectName="AI Chat App"
        />

        <section className="chat-stage flex min-h-0 flex-1 flex-col overflow-y-auto p-3 sm:p-4">
          {selectedConversationId === null ? (
            <div className="empty-state mx-auto flex w-full flex-1 flex-col items-center justify-center gap-5 px-2 py-6 text-center sm:gap-6 sm:py-10">
              <div className="flex items-center justify-center text-3xl font-light text-white" aria-hidden="true">✦</div>
              <div className="max-w-2xl">
                <p className="mb-2 text-[10px] font-bold uppercase tracking-[.22em] text-slate-400">AI CHAT APP</p>
                <h3 className="text-3xl font-bold leading-tight sm:text-4xl">أهلًا بك، كيف أساعدك اليوم؟</h3>
                <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-slate-500 dark:text-slate-300 sm:text-base">
                  ابدأ بفكرة بسيطة، وسنحوّلها معًا إلى خطوات واضحة. اسأل، تعلّم، ابتكر، أو اطلب مساعدة في مشروعك.
                </p>
              </div>
              <div className="grid w-full max-w-3xl grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
                {[
                  { icon: "🪄", title: "طوّر تطبيقك", desc: "حوّل فكرتك إلى خطة تطوير منظمة", prompt: "ساعدني في تطوير تطبيق دردشة احترافي بخطة واضحة." },
                  { icon: "💻", title: "تعلّم البرمجة", desc: "اشرح لي موضوعًا برمجيًا خطوة بخطوة", prompt: "اشرح لي مفهومًا برمجيًا خطوة بخطوة وبالعربية." },
                  { icon: "🗺️", title: "خطّط لمشروع", desc: "رتّب الأفكار إلى مهام قابلة للتنفيذ", prompt: "حوّل فكرة مشروعي إلى خطة تنفيذ ومراحل واضحة." },
                  { icon: "📊", title: "حلّل البيانات", desc: "افهم ملفًا أو مجموعة بيانات", prompt: "ساعدني في تحليل بياناتي واستخراج أهم النتائج." },
                ].map((item) => (
                  <button
                    key={item.title}
                    type="button"
                    onClick={() => { setComposerValue(item.prompt); setStatus("تم وضع اقتراح في مربع الكتابة؛ لن يُرسل تلقائيًا."); }}
                    className="group flex min-h-20 items-start gap-3 rounded-2xl border border-slate-200 bg-white/80 p-4 text-start shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-md dark:border-slate-700 dark:bg-slate-900/75"
                  >
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-xl dark:bg-indigo-950/60">{item.icon}</span>
                    <span className="min-w-0">
                      <span className="block text-sm font-semibold text-slate-800 group-hover:text-indigo-700 dark:text-slate-100 dark:group-hover:text-indigo-300">{item.title}</span>
                      <span className="mt-1 block text-xs leading-5 text-slate-500 dark:text-slate-400">{item.desc}</span>
                    </span>
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-slate-400">اختَر اقتراحًا أو اكتب سؤالك في الأسفل</p>
            </div>
          ) : (
            <div className="chat-surface mx-auto flex min-h-0 w-full max-w-4xl flex-1 flex-col space-y-3 overflow-y-auto rounded-3xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
              <ChatMessage
                role="user"
                text="أريد أن تكون واجهة AI Chat App أكثر احترافية، مع دعم جيد للعربية والهاتف."
                time="الآن"
                canEdit
                onEdit={() => setStatus("تحرير الرسالة غير متصل في المعاينة.")}
                canDelete
                onDelete={() => setStatus("الحذف غير متصل في المعاينة.")}
                canBranch
                onBranch={() => setStatus("تفريع المحادثة غير متصل في المعاينة.")}
                canRemember
                onToggleRemember={() => setStatus("الذاكرة غير متصلة في المعاينة.")}
                onToggleBookmark={() => setStatus("الحفظ في العلامات غير متصل في المعاينة.")}
              />
              <ChatMessage
                role="assistant"
                text={"أهلًا بك! أنا مساعدك الذكي. يمكنني مساعدتك في البرمجة، وتحليل الأفكار، وبناء مشروعك خطوة بخطوة.\n\n**اكتب ما تريد إنجازه، وسنبدأ معًا.**"}
                time="الآن"
                canDelete
                onDelete={() => setStatus("حذف الرسالة غير متصل في المعاينة.")}
                canFeedback
                onFeedback={() => setStatus("التقييم تجريبي ومحلي فقط.")}
                canRegenerate
                onRegenerate={() => setStatus("إعادة التوليد غير متصلة في المعاينة.")}
                onToggleBookmark={() => setStatus("الحفظ في العلامات غير متصل في المعاينة.")}
              />
            </div>
          )}
        </section>

        <ChatComposer
          value={composerValue}
          setValue={setComposerValue}
          onSend={() => {
            const sent = composerValue.trim();
            setStatus(sent ? `رسالة تجريبية محلية فقط: ${sent.slice(0, 90)}` : "لا توجد رسالة تجريبية.");
            setComposerValue("");
          }}
          onStop={() => setStatus("تم إيقاف الإجراء التجريبي فقط.")}
          onInsertCalculator={() => appendCommand("calc")}
          onInsertWebSearch={() => appendCommand("search")}
          onInsertDataAnalysis={() => appendCommand("analyze")}
          onInsertAgent={() => appendCommand("agent")}
          onInsertPython={() => appendCommand("python")}
          onCompareModels={() => setStatus("مقارنة النماذج هنا شكلية ولا تستدعي أي خدمة.")}
          models={[
            { id: "demo-fast", label: "نموذج تجريبي سريع" },
            { id: "demo-reasoning", label: "نموذج تجريبي للاستدلال" },
          ]}
          selectedModel={selectedModel}
          onSelectModel={setSelectedModel}
          onVoiceError={(message) => setStatus(message)}
        />
      </main>

      <div className="sidebar-preview-notice" role="status" aria-live="polite">
        <strong>معاينة آمنة · بيانات وهمية</strong>
        <span>{status}</span>
      </div>

      {settingsOpen ? (
        <div
          className="settings-overlay fixed inset-0 z-[100] flex items-start justify-center overflow-y-auto overscroll-contain bg-black/40 p-2 sm:items-center sm:p-4"
          onClick={(event) => {
            if (event.target === event.currentTarget) setSettingsOpen(false);
          }}
        >
          <section
            className="settings-dialog my-2 w-full max-w-md rounded-3xl border border-slate-200 bg-white p-4 shadow-lg sm:my-8 sm:p-6"
            role="dialog"
            aria-modal="true"
            aria-labelledby="preview-settings-title"
          >
            <div className="sticky top-0 z-10 -mx-4 -mt-4 mb-4 flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-900 sm:-mx-6 sm:-mt-6 sm:px-6">
              <h2 id="preview-settings-title" className="text-lg font-semibold">إعدادات المعاينة</h2>
              <button
                type="button"
                onClick={() => setSettingsOpen(false)}
                aria-label="إغلاق الإعدادات"
                className="rounded-lg px-3 py-2 text-slate-500 hover:bg-slate-100"
              >
                ✕
              </button>
            </div>
            {[
              "الملف الشخصي — تجريبي",
              "تفضيلات الإشعارات — تجريبية",
              "عناوين المحادثات — تجريبي",
              "التلخيص التلقائي — تجريبي",
              "الذاكرة — تجريبية",
              "مفاتيح API — عرض وهمي فقط",
              "الجلسات — تجريبية",
              "الأمان والتحقق بخطوتين — تجريبي",
              "تصدير البيانات — غير متصل",
              "إدارة الحساب — غير متصلة",
            ].map((title, index) => (
              <div key={title} className="settings-section mb-4 rounded-2xl border border-slate-200 p-4">
                <p className="mb-2 text-sm font-medium">{title}</p>
                {index < 4 ? (
                  <label className="flex items-start gap-3 text-sm">
                    <input type="checkbox" />
                    <span>خيار شكلي لا يحفظ أي إعدادات حقيقية.</span>
                  </label>
                ) : (
                  <p className="text-xs leading-6 text-slate-500">قسم تجريبي لا يتصل بالخادم أو قاعدة البيانات.</p>
                )}
              </div>
            ))}
            <p className="text-xs leading-6 text-slate-500">
              هذه نافذة اختبار فقط. جرّب التمرير إلى النهاية، ثم العودة إلى الأعلى، أو الإغلاق بزر ✕ أو Escape أو بالضغط خارج النافذة.
            </p>
          </section>
        </div>
      ) : null}

      <style>{`
        #root { height: 100dvh; min-height: 0; }
        .sidebar-preview-shell { display: flex; width: 100%; height: 100dvh; min-height: 0; overflow: hidden; color: #0f172a; }
        .sidebar-preview-notice {
          position: fixed;
          inset-inline-start: 12px;
          bottom: calc(92px + env(safe-area-inset-bottom));
          z-index: 25;
          display: grid;
          gap: 3px;
          max-width: min(360px, calc(100vw - 24px));
          border: 1px solid var(--ui-border-strong);
          border-radius: 13px;
          padding: 8px 11px;
          background: color-mix(in srgb, var(--ui-surface-solid) 94%, transparent);
          box-shadow: var(--ui-shadow-sm);
          color: var(--ui-text-muted);
          font-size: 10px;
          line-height: 1.5;
          pointer-events: none;
        }
        .sidebar-preview-notice strong { color: var(--ui-accent); font-size: 10px; }
        .sidebar-preview-notice span { display: -webkit-box; overflow: hidden; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
        .dark .sidebar-preview-shell { color: #e2e8f0; }
        @media (max-width: 767px) {
          .modern-sidebar { width: min(286px, 88vw) !important; min-width: min(286px, 88vw) !important; }
          .modern-conversation-menu { max-width: calc(100vw - 40px); }
          .sidebar-preview-notice { bottom: calc(92px + env(safe-area-inset-bottom)); max-width: min(290px, calc(100vw - 24px)); }
        }
      `}</style>
    </div>
  );
}
