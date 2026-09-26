import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import WorkspaceConversationCommentsPanel from "./WorkspaceConversationCommentsPanel";

const listConversationComments = vi.fn();
const createConversationComment = vi.fn();
const updateConversationComment = vi.fn();
const deleteConversationComment = vi.fn();

vi.mock("../lib/workspaceConversationCommentsApi", () => ({
  listConversationComments: (...args) => listConversationComments(...args),
  createConversationComment: (...args) => createConversationComment(...args),
  updateConversationComment: (...args) => updateConversationComment(...args),
  deleteConversationComment: (...args) => deleteConversationComment(...args),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) =>
      ({
        "workspaceComments.title": "تعليقات المحادثة",
        "workspaceComments.hint": "ناقش المحادثة",
        "workspaceComments.refresh": "تحديث",
        "workspaceComments.empty": "لا توجد تعليقات بعد",
        "workspaceComments.placeholder": "اكتب تعليقك...",
        "workspaceComments.visibility": "مرئي للأعضاء",
        "workspaceComments.add": "إضافة تعليق",
        "workspaceComments.edit": "تعديل",
        "workspaceComments.delete": "حذف",
        "workspaceComments.save": "حفظ",
        "workspaceComments.cancel": "إلغاء",
        "workspaceComments.loadError": "تعذر تحميل التعليقات",
        "workspaceComments.saveError": "تعذر حفظ التعليق",
        "workspaceComments.updateError": "تعذر تعديل التعليق",
        "workspaceComments.deleteError": "تعذر حذف التعليق",
      })[key] ?? key,
  }),
}));

describe("WorkspaceConversationCommentsPanel", () => {
  beforeEach(() => {
    listConversationComments.mockReset();
    createConversationComment.mockReset();
    updateConversationComment.mockReset();
    deleteConversationComment.mockReset();
  });

  it("يستخدم Global Toast عند فشل تحميل التعليقات", async () => {
    listConversationComments.mockRejectedValue({
      response: { data: { detail: "رفض الوصول" } },
    });
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    render(
      <WorkspaceConversationCommentsPanel
        workspaceId={7}
        conversationId={10}
      />
    );

    await waitFor(() => {
      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "app:toast",
          detail: { message: "رفض الوصول", type: "error" },
        })
      );
    });

    dispatchSpy.mockRestore();
  });

  it("يعرض التعليقات ويضيف تعليقًا جديدًا", async () => {
    listConversationComments.mockResolvedValue([]);
    createConversationComment.mockResolvedValue({
      id: 1,
      conversation_id: 10,
      user_id: 2,
      user_email: "member@example.com",
      message_id: null,
      content: "ملاحظة جديدة",
      created_at: "2026-09-23T00:00:00Z",
      updated_at: "2026-09-23T00:00:00Z",
    });

    const user = userEvent.setup();
    render(
      <WorkspaceConversationCommentsPanel
        workspaceId={7}
        conversationId={10}
      />
    );

    expect(await screen.findByText("لا توجد تعليقات بعد")).toBeInTheDocument();
    await user.type(screen.getByPlaceholderText("اكتب تعليقك..."), "ملاحظة جديدة");
    await user.click(screen.getByRole("button", { name: "إضافة تعليق" }));

    expect(createConversationComment).toHaveBeenCalledWith(
      7,
      10,
      "ملاحظة جديدة"
    );
    expect(await screen.findByText("ملاحظة جديدة")).toBeInTheDocument();
  });
});
