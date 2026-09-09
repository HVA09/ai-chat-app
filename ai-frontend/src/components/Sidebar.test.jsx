import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, afterEach } from "vitest";
import Sidebar from "./Sidebar";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) => ({
      appName: "مساعد الذكاء الاصطناعي",
      newChat: "محادثة جديدة",
      noChats: "لا توجد محادثات بعد",
      "sidebar.renamePrompt": "اسم المحادثة الجديد:",
      "sidebar.renameTitle": "إعادة تسمية",
      "sidebar.deleteTitle": "حذف",
      "sidebar.confirmDelete": "حذف المحادثة؟",
    })[key] ?? key,
  }),
}));

const sampleConversations = [
  { id: 1, title: "محادثة أولى", created_at: "2026-07-01T10:00:00Z" },
  { id: 2, title: "محادثة ثانية", created_at: "2026-07-02T10:00:00Z" },
];

function renderSidebar(overrides = {}) {
  const props = {
    conversations: sampleConversations,
    onSelectConversation: vi.fn(),
    onNewChat: vi.fn(),
    onRenameConversation: vi.fn(),
    onDeleteConversation: vi.fn(),
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

  it("الحذف ما يصير لو المستخدم ألغى التأكيد", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    const { onDeleteConversation } = renderSidebar();

    await user.click(screen.getAllByTitle("حذف")[0]);
    expect(onDeleteConversation).not.toHaveBeenCalled();
  });
});
