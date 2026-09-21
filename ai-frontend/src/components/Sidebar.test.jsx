import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, afterEach } from "vitest";
import Sidebar from "./Sidebar";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key, variables = {}) => {
      const value = ({
      appName: "مساعد الذكاء الاصطناعي",
      newChat: "محادثة جديدة",
      noChats: "لا توجد محادثات بعد",
      "sidebar.renamePrompt": "اسم المحادثة الجديد:",
      "sidebar.renameTitle": "إعادة تسمية",
      "sidebar.duplicateTitle": "نسخ المحادثة",
      "sidebar.deleteTitle": "حذف",
      "sidebar.editAssistantTitle": "تعديل المساعد",
      "sidebar.deleteAssistantTitle": "حذف المساعد",
      "sidebar.shareAssistantTitle": "مشاركة المساعد مع مساحة العمل",
      "sidebar.unshareAssistantTitle": "إلغاء مشاركة المساعد",
      "sidebar.trashTitle": "سلة المحذوفات",
      "sidebar.permanentDeleteConfirm": "حذف نهائي للمحادثة {{title}}؟",
      "sidebar.bulkTrash": "نقل المحدد إلى سلة المحذوفات",
      "sidebar.confirmDelete": "حذف المحادثة؟",
      "sidebar.foldersTitle": "المجلدات",
      "sidebar.allConversations": "كل المحادثات",
      "sidebar.createFolderTitle": "إنشاء مجلد",
      "sidebar.folderCreatePrompt": "اسم المجلد:",
      "sidebar.folderRenamePrompt": "اسم المجلد الجديد:",
      "sidebar.renameFolderTitle": "إعادة تسمية المجلد",
      "sidebar.deleteFolderTitle": "حذف المجلد",
      "sidebar.folderDeleteConfirm": "حذف المجلد {{name}}؟",
      "sidebar.moveFolderTitle": "نقل إلى مجلد",
      "sidebar.noFolder": "بدون مجلد",
      "sidebar.savedPromptsTitle": "الموجهات المحفوظة",
      "sidebar.createSavedPromptTitle": "إنشاء موجه محفوظ",
      "sidebar.editSavedPromptTitle": "تعديل الموجه المحفوظ",
      "sidebar.deleteSavedPromptTitle": "حذف الموجه المحفوظ",
      "sidebar.noSavedPrompts": "لا توجد موجهات محفوظة",
      "bookmarks.title": "المحفوظات",
      "bookmarks.empty": "لا توجد رسائل محفوظة بعد",
      "sidebar.selectConversation": "تحديد {{title}}",
      "sidebar.selectAllVisible": "تحديد الكل الظاهر",
      "sidebar.bulkSelected": "{{count}} محددة",
      "sidebar.loadMore": "تحميل المزيد",
      "sidebar.loadingMore": "جارٍ التحميل...",
      "sidebar.bulkArchive": "أرشفة المحدد",
      "sidebar.bulkUnarchive": "إلغاء أرشفة المحدد",
      "sidebar.bulkDelete": "حذف المحدد",
      "sidebar.bulkExport": "تصدير المحدد",
      "sidebar.bulkMoveTitle": "نقل المحدد إلى...",
      "sidebar.clearSelection": "إلغاء التحديد",
      "sidebar.workspaceSelectTitle": "مساحة العمل",
      "sidebar.workspaceCreateTitle": "إنشاء مساحة عمل",
      "sidebar.workspaceRenameTitle": "إعادة تسمية مساحة العمل",
      "sidebar.bulkDeleteConfirm": "حذف {{count}} محادثات؟",
      "sidebar.importConversation": "استيراد محادثة",
      "sidebar.importConversationTitle": "استيراد محادثة من ملف JSON",
    })[key] ?? key;

      return value.replace(/\{\{(\w+)\}\}/g, (_, name) =>
        variables[name] === undefined ? `{{${name}}}` : String(variables[name])
      );
    },
  }),
}));

const sampleConversations = [
  {
    id: 1,
    title: "محادثة أولى",
    created_at: "2026-07-01T10:00:00Z",
    folder_id: 10,
    search_snippet: "ناقشنا خطة العمل للمشروع الجديد اليوم.",
  },
  { id: 2, title: "محادثة ثانية", created_at: "2026-07-02T10:00:00Z", folder_id: null },
];
const sampleWorkspaces = [
  { id: 1, name: "Personal", role: "owner", created_at: "2026-07-01T10:00:00Z" },
  { id: 2, name: "Research", role: "owner", created_at: "2026-07-02T10:00:00Z" },
];
const sampleFolders = [
  { id: 10, name: "عمل", workspace_id: 1, created_at: "2026-07-01T10:00:00Z" },
  { id: 20, name: "دراسة", workspace_id: null, created_at: "2026-07-02T10:00:00Z" },
];

function renderSidebar(overrides = {}) {
  const props = {
    conversations: sampleConversations,
    assistants: [{ id: 10, name: "مساعد الفريق", description: "مساعد", is_shared: false, can_edit: true }],
    onSelectConversation: vi.fn(),
    onNewChat: vi.fn(),
    onImportConversation: vi.fn(),
    onRenameConversation: vi.fn(),
    onDeleteConversation: vi.fn(),
    onToggleShareAssistant: vi.fn(),
    selectedWorkspaceId: 7,
    onTogglePinConversation: vi.fn(),
    onDuplicateConversation: vi.fn(),
    savedPrompts: [{ id: 10, name: "تلخيص", content: "لخص النص في 5 نقاط." }],
    bookmarkedMessages: [
      { message_id: 20, conversation_id: 1, conversation_title: "محادثة أولى", message_index: 2, content: "رد مهم" },
    ],
    onOpenBookmarkedMessage: vi.fn(),
    onCreateSavedPrompt: vi.fn(),
    onRenameSavedPrompt: vi.fn(),
    onDeleteSavedPrompt: vi.fn(),
    onUseSavedPrompt: vi.fn(),
    onToggleArchiveConversation: vi.fn(),
    onToggleTrashConversation: vi.fn(),
    folders: sampleFolders,
    workspaces: sampleWorkspaces,
    selectedWorkspaceId: 1,
    selectedWorkspaceRole: "owner",
    onSelectWorkspace: vi.fn(),
    onCreateWorkspace: vi.fn(),
    onRenameWorkspace: vi.fn(),
    selectedFolderId: null,
    onSelectFolder: vi.fn(),
    onCreateFolder: vi.fn(),
    onRenameFolder: vi.fn(),
    onDeleteFolder: vi.fn(),
    onMoveConversationToFolder: vi.fn(),
    selectedConversationIds: [],
    onToggleConversationSelection: vi.fn(),
    onToggleSelectAllVisible: vi.fn(),
    onClearSelectedConversations: vi.fn(),
    onLoadMore: vi.fn(),
    onBulkArchive: vi.fn(),
    onBulkDelete: vi.fn(),
    onBulkExport: vi.fn(),
    onBulkMoveToFolder: vi.fn(),
    showArchived: false,
    onShowArchived: vi.fn(),
    onShowTrash: vi.fn(),
    searchValue: "",
    onSearchChange: vi.fn(),
    loading: false,
    ...overrides,
  };
  render(<Sidebar {...props} />);
  return props;
}

describe("Sidebar", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("يعرض رسالة عدم وجود محادثات لما تكون القائمة فاضية", () => {
    renderSidebar({ conversations: [] });
    expect(screen.getByText("لا توجد محادثات بعد")).toBeInTheDocument();
  });

  it("يعرض كل المحادثات الممرّرة له (قراءة البيانات)", () => {
    renderSidebar();
    expect(screen.getByText("محادثة أولى")).toBeInTheDocument();
    expect(screen.getByText("محادثة ثانية")).toBeInTheDocument();
  });

  it("الضغط على محادثة ينادي onSelectConversation بالـ id الصحيح", async () => {
    const user = userEvent.setup();
    const { onSelectConversation } = renderSidebar();
    await user.click(screen.getByText("محادثة أولى"));
    expect(onSelectConversation).toHaveBeenCalledWith(1);
  });

  it("نسخ المحادثة يستدعي المعالج بالمعرف الصحيح", async () => {
    const user = userEvent.setup();
    const { onDuplicateConversation } = renderSidebar();
    await user.click(screen.getAllByTitle("نسخ المحادثة")[0]);
    expect(onDuplicateConversation).toHaveBeenCalledWith(1);
  });

  it("بحث المحادثات يرسل القيمة إلى المعالج بعد مهلة قصيرة", () => {
    vi.useFakeTimers();
    try {
      const onSearchChange = vi.fn();
      renderSidebar({ onSearchChange });

      const input = screen.getByRole("searchbox");
      fireEvent.change(input, { target: { value: "عمل" } });
      vi.advanceTimersByTime(350);

      expect(onSearchChange).toHaveBeenLastCalledWith("عمل");
    } finally {
      vi.useRealTimers();
    }
  });

  it("يعرض مقتطف المطابقة ويُبرز كلمة البحث", () => {
    renderSidebar({
      searchValue: "خطة العمل",
    });
    expect(screen.getByText("خطة العمل")).toBeInTheDocument();
    expect(screen.getByText("ناقشنا ")).toBeInTheDocument();
  });

  it("تحميل المزيد يستدعي المعالج", async () => {
    const user = userEvent.setup();
    const { onLoadMore } = renderSidebar({ hasMore: true });
    await user.click(screen.getByText("تحميل المزيد"));
    expect(onLoadMore).toHaveBeenCalled();
  });

  it("استيراد محادثة يمرر الملف إلى المعالج", async () => {
    const { onImportConversation } = renderSidebar();
    const input = screen.getByLabelText("استيراد محادثة");
    const file = new File(
      [
        JSON.stringify({
          title: "محادثة مستوردة",
          messages: [{ role: "user", content: "مرحبًا" }],
        }),
      ],
      "conversation.json",
      { type: "application/json" }
    );

    fireEvent.change(input, { target: { files: [file] } });
    expect(onImportConversation).toHaveBeenCalledWith(file);
  });

  it("تصدير المحادثات المحددة يستدعي onBulkExport", async () => {
    const user = userEvent.setup();
    const { onBulkExport } = renderSidebar({ selectedConversationIds: [1] });
    await user.click(screen.getByText("تصدير المحدد"));
    expect(onBulkExport).toHaveBeenCalled();
  });

  it("زر محادثة جديدة ينادي onNewChat", async () => {
    const user = userEvent.setup();
    const { onNewChat } = renderSidebar();
    await user.click(screen.getByText("محادثة جديدة"));
    expect(onNewChat).toHaveBeenCalled();
  });

  it("إعادة التسمية تنادي onRenameConversation بالعنوان الجديد (تعديل)", async () => {
    vi.spyOn(window, "prompt").mockReturnValue("اسم معدّل");
    const user = userEvent.setup();
    const { onRenameConversation, onSelectConversation } = renderSidebar();

    await user.click(screen.getAllByTitle("إعادة تسمية")[0]);

    expect(onRenameConversation).toHaveBeenCalledWith(1, "اسم معدّل");
    expect(onSelectConversation).not.toHaveBeenCalled();
  });

  it("إلغاء نافذة إعادة التسمية ما يستدعي onRenameConversation", async () => {
    vi.spyOn(window, "prompt").mockReturnValue(null);
    const user = userEvent.setup();
    const { onRenameConversation } = renderSidebar();

    await user.click(screen.getAllByTitle("إعادة تسمية")[0]);
    expect(onRenameConversation).not.toHaveBeenCalled();
  });

  it("نقل المحادثة إلى سلة المحذوفات يستدعي onToggleTrashConversation", async () => {
    const user = userEvent.setup();
    const { onToggleTrashConversation, onSelectConversation } = renderSidebar();

    await user.click(screen.getAllByTitle("سلة المحذوفات")[0]);

    expect(onToggleTrashConversation).toHaveBeenCalledWith(1);
    expect(onSelectConversation).not.toHaveBeenCalled();
  });

  it("زر سلة المحذوفات يستخدم onToggleTrashConversation مباشرة", async () => {
    const user = userEvent.setup();
    const { onToggleTrashConversation } = renderSidebar();

    await user.click(screen.getAllByTitle("سلة المحذوفات")[0]);

    expect(onToggleTrashConversation).toHaveBeenCalledWith(1);
  });

  it("يستطيع تغيير مساحة العمل", async () => {
    const user = userEvent.setup();
    const { onSelectWorkspace } = renderSidebar();
    await user.selectOptions(screen.getByLabelText("مساحة العمل"), "2");
    expect(onSelectWorkspace).toHaveBeenCalledWith("2");
  });

  it("يستطيع اختيار مجلد للمحادثات", async () => {
    const user = userEvent.setup();
    const { onSelectFolder } = renderSidebar();
    await user.click(screen.getByRole("button", { name: /عمل/ }));
    expect(onSelectFolder).toHaveBeenCalledWith(10);
  });

  it("نقل محادثة يرسل معرف المجلد", async () => {
    const user = userEvent.setup();
    const { onMoveConversationToFolder } = renderSidebar();
    await user.selectOptions(screen.getAllByLabelText("نقل إلى مجلد")[0], "20");
    expect(onMoveConversationToFolder).toHaveBeenCalledWith(1, "20");
  });

  it("إنشاء مساحة عمل يستدعي المعالج", async () => {
    const user = userEvent.setup();
    const { onCreateWorkspace } = renderSidebar();
    await user.click(screen.getByTitle("إنشاء مساحة عمل"));
    expect(onCreateWorkspace).toHaveBeenCalled();
  });

  it("زر إنشاء مجلد يستدعي المعالج", async () => {
    const user = userEvent.setup();
    const { onCreateFolder } = renderSidebar();
    await user.click(screen.getByTitle("إنشاء مجلد"));
    expect(onCreateFolder).toHaveBeenCalled();
  });

  it("يستطيع تحديد محادثة للم actions الجماعية", async () => {
    const user = userEvent.setup();
    const { onToggleConversationSelection } = renderSidebar();
    await user.click(screen.getByRole("checkbox", { name: "تحديد محادثة أولى" }));
    expect(onToggleConversationSelection).toHaveBeenCalledWith(1);
  });

  it("يستطيع تحديد كل المحادثات الظاهرة", async () => {
    const user = userEvent.setup();
    const { onToggleSelectAllVisible } = renderSidebar();
    await user.click(screen.getByRole("checkbox", { name: "تحديد الكل الظاهر" }));
    expect(onToggleSelectAllVisible).toHaveBeenCalledWith([1, 2]);
  });

  it("يعرض المحفوظات ويفتح المحادثة عند اختيار رسالة محفوظة", async () => {
    const user = userEvent.setup();
    const { onOpenBookmarkedMessage } = renderSidebar();
    expect(screen.getByText("المحفوظات")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /محادثة أولى/ }));
    expect(onOpenBookmarkedMessage).toHaveBeenCalledWith(
      expect.objectContaining({ message_id: 20, conversation_id: 1 })
    );
  });

  it("يعرض أدوات الإجراءات الجماعية عند وجود تحديد", () => {
    renderSidebar({ selectedConversationIds: [1] });
    expect(screen.getByText("أرشفة المحدد")).toBeInTheDocument();
    expect(screen.getByText("نقل المحدد إلى سلة المحذوفات")).toBeInTheDocument();
  });

  it("يستطيع نقل المحدد إلى مجلد", async () => {
    const user = userEvent.setup();
    const { onBulkMoveToFolder } = renderSidebar({ selectedConversationIds: [1] });
    await user.selectOptions(screen.getByRole("combobox", { name: "نقل المحدد إلى..." }), "20");
    expect(onBulkMoveToFolder).toHaveBeenCalledWith("20");
  });

  it("سلة المحذوفات في وضع السلة تصبح حذفًا نهائيًا", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    const { onDeleteConversation, onToggleTrashConversation } = renderSidebar({
      showTrash: true,
    });

    await user.click(screen.getAllByTitle("حذف")[0]);

    expect(onDeleteConversation).toHaveBeenCalledWith(1);
    expect(onToggleTrashConversation).not.toHaveBeenCalled();
  });

  it("استخدام موجه محفوظ يستدعي المعالج بالنص", async () => {
    const user = userEvent.setup();
    const { onUseSavedPrompt } = renderSidebar();
    await user.click(screen.getByRole("button", { name: /تلخيص/ }));
    expect(onUseSavedPrompt).toHaveBeenCalledWith("لخص النص في 5 نقاط.");
  });

  it("زر إنشاء موجه محفوظ يستدعي المعالج", async () => {
    const user = userEvent.setup();
    const { onCreateSavedPrompt } = renderSidebar();
    await user.click(screen.getByTitle("إنشاء موجه محفوظ"));
    expect(onCreateSavedPrompt).toHaveBeenCalled();
  });

  it("حذف موجه محفوظ يستدعي المعالج", async () => {
    const user = userEvent.setup();
    const { onDeleteSavedPrompt } = renderSidebar();
    await user.click(screen.getByTitle("حذف الموجه المحفوظ"));
    expect(onDeleteSavedPrompt).toHaveBeenCalledWith(10, "تلخيص");
  });

  it("مشاركة المساعد تنادي onToggleShareAssistant", async () => {
    const user = userEvent.setup();
    const { onToggleShareAssistant } = renderSidebar();
    await user.click(screen.getByTitle("مشاركة المساعد مع مساحة العمل"));
    expect(onToggleShareAssistant).toHaveBeenCalledWith(
      expect.objectContaining({ id: 10, name: "مساعد الفريق" })
    );
  });

  it("المساعد المشترك لا يعرض تعديل وحذف", () => {
    renderSidebar({
      assistants: [{ id: 10, name: "مساعد مشترك", description: "مشترك", is_shared: true, can_edit: false }],
    });
    expect(screen.queryByTitle("تعديل المساعد")).not.toBeInTheDocument();
    expect(screen.queryByTitle("حذف المساعد")).not.toBeInTheDocument();
  });

  it("الحذف ما يصير لو المستخدم ألغى التأكيد", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    const { onDeleteConversation } = renderSidebar();

    await user.click(screen.getAllByTitle("سلة المحذوفات")[0]);
    expect(onDeleteConversation).not.toHaveBeenCalled();
  });
});


it("عضو مساحة العمل لا يرى أزرار إدارة مجلدات مساحة العمل", () => {
  renderSidebar({
    selectedWorkspaceRole: "member",
    folders: sampleFolders.map((folder) => ({ ...folder, workspace_id: 1 })),
  });
  expect(screen.queryByTitle("إعادة تسمية المجلد")).not.toBeInTheDocument();
  expect(screen.queryByTitle("حذف المجلد")).not.toBeInTheDocument();
});
