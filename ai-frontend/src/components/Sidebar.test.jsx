import { render, screen } from "@testing-library/react";
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
      "sidebar.deleteTitle": "حذف",
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
      "sidebar.selectConversation": "تحديد {{title}}",
      "sidebar.selectAllVisible": "تحديد الكل الظاهر",
      "sidebar.bulkSelected": "{{count}} محددة",
      "sidebar.bulkArchive": "أرشفة المحدد",
      "sidebar.bulkUnarchive": "إلغاء أرشفة المحدد",
      "sidebar.bulkDelete": "حذف المحدد",
      "sidebar.bulkMoveTitle": "نقل المحدد إلى...",
      "sidebar.clearSelection": "إلغاء التحديد",
      "sidebar.workspaceSelectTitle": "مساحة العمل",
      "sidebar.workspaceCreateTitle": "إنشاء مساحة عمل",
      "sidebar.workspaceRenameTitle": "إعادة تسمية مساحة العمل",
      "sidebar.bulkDeleteConfirm": "حذف {{count}} محادثات؟",
    })[key] ?? key;

      return value.replace(/\{\{(\w+)\}\}/g, (_, name) =>
        variables[name] === undefined ? `{{${name}}}` : String(variables[name])
      );
    },
  }),
}));

const sampleConversations = [
  { id: 1, title: "محادثة أولى", created_at: "2026-07-01T10:00:00Z", folder_id: 10 },
  { id: 2, title: "محادثة ثانية", created_at: "2026-07-02T10:00:00Z", folder_id: null },
];
const sampleWorkspaces = [
  { id: 1, name: "Personal", role: "owner", created_at: "2026-07-01T10:00:00Z" },
  { id: 2, name: "Research", role: "owner", created_at: "2026-07-02T10:00:00Z" },
];
const sampleFolders = [
  { id: 10, name: "عمل", created_at: "2026-07-01T10:00:00Z" },
  { id: 20, name: "دراسة", created_at: "2026-07-02T10:00:00Z" },
];

function renderSidebar(overrides = {}) {
  const props = {
    conversations: sampleConversations,
    onSelectConversation: vi.fn(),
    onNewChat: vi.fn(),
    onRenameConversation: vi.fn(),
    onDeleteConversation: vi.fn(),
    onTogglePinConversation: vi.fn(),
    onToggleArchiveConversation: vi.fn(),
    folders: sampleFolders,
    workspaces: sampleWorkspaces,
    selectedWorkspaceId: 1,
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
    onBulkArchive: vi.fn(),
    onBulkDelete: vi.fn(),
    onBulkMoveToFolder: vi.fn(),
    showArchived: false,
    onShowArchived: vi.fn(),
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

  it("بحث المحادثات يرسل القيمة إلى المعالج بعد مهلة قصيرة", async () => {
    vi.useFakeTimers();
    try {
      const onSearchChange = vi.fn();
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      renderSidebar({ onSearchChange });

      const input = screen.getByRole("searchbox");
      await user.type(input, "عمل");
      vi.advanceTimersByTime(350);

      expect(onSearchChange).toHaveBeenLastCalledWith("عمل");
    } finally {
      vi.useRealTimers();
    }
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

  it("الحذف يستدعي onDeleteConversation بعد تأكيد المستخدم (حذف)", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    const { onDeleteConversation, onSelectConversation } = renderSidebar();

    await user.click(screen.getAllByTitle("حذف")[0]);

    expect(onDeleteConversation).toHaveBeenCalledWith(1);
    expect(onSelectConversation).not.toHaveBeenCalled();
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

  it("يعرض أدوات الإجراءات الجماعية عند وجود تحديد", () => {
    renderSidebar({ selectedConversationIds: [1] });
    expect(screen.getByText("أرشفة المحدد")).toBeInTheDocument();
    expect(screen.getByText("حذف المحدد")).toBeInTheDocument();
  });

  it("يستطيع نقل المحدد إلى مجلد", async () => {
    const user = userEvent.setup();
    const { onBulkMoveToFolder } = renderSidebar({ selectedConversationIds: [1] });
    await user.selectOptions(screen.getByRole("combobox", { name: "نقل المحدد إلى..." }), "20");
    expect(onBulkMoveToFolder).toHaveBeenCalledWith("20");
  });

  it("الحذف ما يصير لو المستخدم ألغى التأكيد", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    const { onDeleteConversation } = renderSidebar();

    await user.click(screen.getAllByTitle("حذف")[0]);
    expect(onDeleteConversation).not.toHaveBeenCalled();
  });
});
