import { useEffect, useMemo, useState } from "react";
import SidebarModern from "./components/SidebarModern";
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
  const [selectedConversationId, setSelectedConversationId] = useState(101);
  const [showArchived, setShowArchived] = useState(false);
  const [showTrash, setShowTrash] = useState(false);
  const [status, setStatus] = useState("هذه معاينة واجهة معزولة؛ الإجراءات تغيّر بيانات تجريبية محلية فقط.");
  const [composerValue, setComposerValue] = useState("");
  const [selectedModel, setSelectedModel] = useState("demo-fast");
  const [settingsOpen, setSettingsOpen] = useState(false);

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
        onNewChat={() => setStatus("هذا إجراء تجريبي محلي ولا ينشئ محادثة حقيقية.")}
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

      <main className="sidebar-preview-main">
        <header className="sidebar-preview-header">
          <button
            type="button"
            className="sidebar-preview-open-button"
            onClick={() => window.dispatchEvent(new Event("app:open-sidebar"))}
          >
            ☰ فتح القائمة
          </button>
          <button
            type="button"
            className="sidebar-preview-settings-button"
            onClick={() => setSettingsOpen(true)}
          >
            ⚙️ اختبار الإعدادات
          </button>
          <span className="sidebar-preview-badge">معاينة آمنة — بيانات وهمية</span>
        </header>

        <section className="sidebar-preview-content">
          <div className="sidebar-preview-chat-heading">
            <div className="sidebar-preview-ai-mark" aria-hidden="true">✦</div>
            <div className="min-w-0">
              <h1>مساعد في البرمجة</h1>
              <p><span className="sidebar-preview-live-dot" /> متصل الآن · نموذج تجريبي</p>
            </div>
            <span className="sidebar-preview-concept-tag">التصميم ٣</span>
          </div>

          <div className="sidebar-preview-transcript" aria-label="محادثة تجريبية">
            <div className="sidebar-preview-message sidebar-preview-user-message">
              <div className="sidebar-preview-user-bubble">مرحبًا، كيف يمكنني مساعدتك اليوم؟</div>
              <span className="sidebar-preview-message-time">أنت · الآن</span>
            </div>

            <div className="sidebar-preview-message sidebar-preview-assistant-message">
              <div className="sidebar-preview-ai-avatar" aria-hidden="true">✦</div>
              <div className="sidebar-preview-assistant-content">
                <div className="sidebar-preview-assistant-bubble">
                  <p>أهلًا بك! أنا مساعدك الذكي. يمكنني مساعدتك في البرمجة، وتحليل الأفكار، وبناء مشروعك خطوة بخطوة.</p>
                  <p>اكتب ما تريد إنجازه، وسنبدأ معًا.</p>
                </div>
                <div className="sidebar-preview-suggestion-row">
                  <span>اكتب كودًا</span>
                  <span>حلّل ملفًا</span>
                  <span>خطّط لمشروع</span>
                </div>
                <span className="sidebar-preview-message-time">المساعد · الآن</span>
              </div>
            </div>
          </div>

          <div className="sidebar-preview-status-card" role="status" aria-live="polite">
            <span className="sidebar-preview-status-dot" />
            <div>
              <strong>حالة المعاينة</strong>
              <p>{status}</p>
            </div>
          </div>

          <details className="sidebar-preview-checks">
            <summary>اختبارات الواجهة والقائمة</summary>
            <p>١. اضغط «المزيد» بجانب محادثة تجريبية، ثم أغلق القائمة بالنقر خارجها أو بمفتاح Escape.</p>
            <p>٢. جرّب فتح القائمة قرب أسفل الشريط الجانبي؛ يجب أن تتكيف مع مساحة الشاشة.</p>
            <p>٣. جرّب نقل محادثة إلى مجلد أو مشروع، وتعديل الوسوم، والتثبيت، والأرشفة.</p>
            <p>٤. افتح الإعدادات من الشريط الجانبي أو من زر «اختبار الإعدادات» في الأعلى، ثم اختبر التمرير والإغلاق.</p>
          </details>

          <div className="sidebar-preview-status-line">{countLabel}</div>
          <p className="sidebar-preview-safety-note">
            معاينة مستقلة ببيانات وهمية فقط. لا يوجد اتصال بالخادم أو Supabase، ولا تسجّل دخولًا أو تضع بيانات حقيقية. التغييرات تختفي عند تحديث الصفحة.
          </p>
        </section>

        <div className="sidebar-preview-composer">
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
        </div>
      </main>

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
        #root { min-height: 100%; }
        .sidebar-preview-shell { display: flex; height: 100dvh; min-height: 100dvh; overflow: hidden; color: #0f172a; }
        .sidebar-preview-main { display: flex; flex: 1 1 auto; flex-direction: column; min-width: 0; min-height: 0; overflow: hidden; background: linear-gradient(145deg, #f8fafc, #eef2ff 55%, #f8fafc); }
        .sidebar-preview-settings-button { display: inline-flex; align-items: center; justify-content: center; gap: 6px; border: 1px solid #cbd5e1; border-radius: 10px; padding: 9px 12px; background: #fff; color: #334155; font-size: 12px; font-weight: 700; }
        .sidebar-preview-composer { flex: 0 0 auto; min-width: 0; border-top: 1px solid rgba(148,163,184,.24); background: #f8fafc; }
        .sidebar-preview-composer .chat-composer { border-top: 0; }
        .sidebar-preview-content { flex: 1 1 auto; min-height: 0; width: 100%; overflow-y: auto; overscroll-behavior: contain; margin: 0 auto; padding: clamp(16px, 3vw, 30px) clamp(14px, 3vw, 28px) 28px; }
        .sidebar-preview-header { position: sticky; top: 0; z-index: 20; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; padding: 10px clamp(12px, 3vw, 24px); border-bottom: 1px solid rgba(148,163,184,.25); background: rgba(255,255,255,.78); backdrop-filter: blur(16px); }
        .sidebar-preview-open-button { display: none; border: 1px solid #dbe3ef; border-radius: 10px; padding: 9px 12px; background: white; color: #334155; font-size: 13px; font-weight: 600; }
        .sidebar-preview-badge { display: inline-flex; align-items: center; border: 1px solid rgba(129,140,248,.25); border-radius: 999px; padding: 5px 10px; background: rgba(99,102,241,.08); color: #5145cd; font-size: 11px; font-weight: 700; }
        .sidebar-preview-chat-heading { display: flex; align-items: center; gap: 12px; width: min(920px, 100%); margin: 0 auto 24px; padding: 12px 2px 18px; border-bottom: 1px solid rgba(129,140,248,.17); }
        .sidebar-preview-ai-mark { display: grid; width: 42px; height: 42px; flex: 0 0 auto; place-items: center; border-radius: 15px; background: linear-gradient(135deg,#7c6cf2,#2ea7dd); color: white; font-size: 24px; box-shadow: 0 8px 22px rgba(99,102,241,.22); }
        .sidebar-preview-chat-heading h1 { margin: 0; color: #172554; font-size: 17px; font-weight: 800; line-height: 1.4; }
        .sidebar-preview-chat-heading p { display: flex; align-items: center; gap: 6px; margin-top: 3px; color: #64748b; font-size: 11px; }
        .sidebar-preview-live-dot { width: 7px; height: 7px; border-radius: 50%; background: #22c55e; box-shadow: 0 0 0 3px rgba(34,197,94,.10); }
        .sidebar-preview-concept-tag { margin-inline-start: auto; border: 1px solid rgba(99,102,241,.18); border-radius: 999px; padding: 5px 9px; color: #6254e8; background: rgba(99,102,241,.07); font-size: 10px; font-weight: 800; white-space: nowrap; }
        .sidebar-preview-transcript { display: grid; gap: 24px; width: min(820px, 100%); margin: 0 auto; padding: 4px 0 18px; }
        .sidebar-preview-message { display: flex; gap: 10px; }
        .sidebar-preview-user-message { align-items: flex-end; flex-direction: column; }
        .sidebar-preview-user-bubble { max-width: 84%; border: 1px solid rgba(255,255,255,.28); border-radius: 20px 20px 7px 20px; padding: 13px 16px; background: linear-gradient(135deg,#7568ef,#398de8); color: white; font-size: 14px; line-height: 1.8; box-shadow: 0 8px 24px rgba(79,70,229,.16); }
        .sidebar-preview-message-time { color: #94a3b8; font-size: 10px; }
        .sidebar-preview-assistant-message { align-items: flex-start; }
        .sidebar-preview-ai-avatar { display: grid; width: 30px; height: 30px; flex: 0 0 auto; place-items: center; border: 1px solid rgba(99,102,241,.19); border-radius: 11px; background: linear-gradient(135deg,rgba(14,165,233,.16),rgba(129,140,248,.17)); color: #5145cd; font-size: 17px; }
        .sidebar-preview-assistant-content { display: grid; justify-items: start; gap: 10px; min-width: 0; max-width: calc(100% - 40px); }
        .sidebar-preview-assistant-bubble { border: 1px solid rgba(129,140,248,.16); border-radius: 7px 20px 20px 20px; padding: 16px 18px; background: rgba(255,255,255,.84); color: #334155; font-size: 14px; line-height: 1.9; box-shadow: 0 8px 28px rgba(49,46,129,.05); }
        .sidebar-preview-assistant-bubble p + p { margin-top: 8px; }
        .sidebar-preview-suggestion-row { display: flex; flex-wrap: wrap; gap: 7px; }
        .sidebar-preview-suggestion-row span { border: 1px solid rgba(99,102,241,.18); border-radius: 999px; padding: 6px 10px; background: rgba(255,255,255,.65); color: #5b5da8; font-size: 10px; }
        .sidebar-preview-status-card { display: flex; align-items: flex-start; gap: 10px; width: min(820px, 100%); margin: 10px auto 0; border: 1px solid rgba(129,140,248,.18); border-radius: 15px; padding: 12px 14px; background: rgba(255,255,255,.58); }
        .sidebar-preview-status-card strong { color: #334155; font-size: 11px; }
        .sidebar-preview-status-card p { margin-top: 3px; color: #64748b; font-size: 11px; line-height: 1.6; }
        .sidebar-preview-status-dot { width: 8px; height: 8px; flex: 0 0 auto; margin-top: 4px; border-radius: 50%; background: #16a34a; box-shadow: 0 0 0 4px rgba(22,163,74,.1); }
        .sidebar-preview-checks { width: min(820px, 100%); margin: 16px auto 0; border: 1px solid rgba(129,140,248,.17); border-radius: 15px; padding: 12px 14px; background: rgba(255,255,255,.55); }
        .sidebar-preview-checks summary { cursor: pointer; color: #5145cd; font-size: 12px; font-weight: 800; }
        .sidebar-preview-checks p { margin-top: 10px; color: #64748b; font-size: 11px; line-height: 1.8; }
        .sidebar-preview-status-line { width: min(820px, 100%); margin: 12px auto 0; color: #64748b; font-size: 10px; font-weight: 700; }
        .sidebar-preview-safety-note { width: min(820px, 100%); margin: 12px auto 0; border-inline-start: 3px solid rgba(99,102,241,.35); padding-inline-start: 10px; color: #94a3b8; font-size: 10px; line-height: 1.7; }
        .dark .sidebar-preview-chat-heading h1 { color: #eef2ff; }
        .dark .sidebar-preview-assistant-bubble { border-color: rgba(129,140,248,.18); background: rgba(15,26,51,.76); color: #dbeafe; }
        .dark .sidebar-preview-user-bubble { background: linear-gradient(135deg,#4c43b9,#245bb5); }
        .dark .sidebar-preview-suggestion-row span { background: rgba(15,26,51,.6); color: #c4c5ff; }
        .dark .sidebar-preview-status-card, .dark .sidebar-preview-checks { background: rgba(15,26,51,.58); border-color: rgba(129,140,248,.18); }
        .dark .sidebar-preview-status-card strong { color: #e2e8f0; }
        .dark .sidebar-preview-status-card p, .dark .sidebar-preview-checks p { color: #a8b4d0; }
        .dark .sidebar-preview-chat-heading p { color: #a8b4d0; }
        .dark .sidebar-preview-concept-tag { background: rgba(129,116,255,.13); color: #c4b5fd; }
        .sidebar-preview-status-card { display: flex; gap: 12px; align-items: flex-start; margin-top: 28px; border: 1px solid #dbeafe; border-radius: 16px; padding: 16px; background: rgba(255,255,255,.88); box-shadow: 0 10px 30px rgba(15,23,42,.045); }
        .sidebar-preview-status-dot { width: 10px; height: 10px; flex: 0 0 auto; margin-top: 5px; border-radius: 50%; background: #16a34a; box-shadow: 0 0 0 5px rgba(22,163,74,.1); }
        .sidebar-preview-status-card strong { font-size: 13px; }
        .sidebar-preview-status-card p { margin-top: 5px; color: #475569; font-size: 13px; line-height: 1.8; }
        .sidebar-preview-checks { display: grid; gap: 12px; margin-top: 24px; border: 1px solid #e2e8f0; border-radius: 16px; padding: 18px; background: rgba(255,255,255,.72); }
        .sidebar-preview-checks h2 { font-size: 15px; font-weight: 800; }
        .sidebar-preview-checks p { color: #475569; font-size: 13px; line-height: 1.85; }
        .sidebar-preview-status-line { margin-top: 20px; color: #64748b; font-size: 12px; font-weight: 700; }
        .sidebar-preview-safety-note { margin-top: 16px; border-inline-start: 3px solid #94a3b8; padding-inline-start: 12px; color: #64748b; font-size: 11px; line-height: 1.8; }
        @media (max-width: 767px) {
          .sidebar-preview-open-button { display: inline-flex; }
          .modern-sidebar { width: min(286px, 88vw) !important; min-width: min(286px, 88vw) !important; }
          .modern-conversation-menu { max-width: calc(100vw - 40px); }
          .sidebar-preview-content { padding-top: 12px; padding-bottom: 18px; }
          .sidebar-preview-chat-heading { margin-bottom: 16px; padding-bottom: 12px; }
          .sidebar-preview-ai-mark { width: 36px; height: 36px; border-radius: 12px; }
          .sidebar-preview-chat-heading h1 { font-size: 15px; }
          .sidebar-preview-transcript { gap: 18px; }
          .sidebar-preview-user-bubble { max-width: 92%; font-size: 13px; padding: 11px 13px; }
          .sidebar-preview-assistant-bubble { padding: 13px; font-size: 13px; line-height: 1.8; }
          .sidebar-preview-concept-tag { font-size: 9px; }
          .sidebar-preview-badge { max-width: 120px; font-size: 9px; }
        }
      `}</style>
    </div>
  );
}
