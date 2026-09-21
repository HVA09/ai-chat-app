import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import SharedConversationPage from "./SharedConversationPage";

const getSharedConversation = vi.fn();
const accessProtectedSharedConversation = vi.fn();

vi.mock("../lib/sharedConversationsApi", () => ({
  getSharedConversation: (...args) => getSharedConversation(...args),
  accessProtectedSharedConversation: (...args) => accessProtectedSharedConversation(...args),
}));

vi.mock("../i18n", () => ({
  default: {},
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    i18n: { language: "ar" },
    t: (key) =>
      ({
        "sharing.passwordRequiredTitle": "هذا الرابط محمي بكلمة مرور",
        "sharing.passwordRequiredHint": "أدخل كلمة المرور لعرض المحادثة.",
        "sharing.passwordPlaceholder": "كلمة المرور",
        "sharing.unlock": "فتح الرابط",
        "sharing.unlocking": "جارٍ التحقق...",
        "sharing.invalidPassword": "كلمة المرور غير صحيحة",
        "sharing.expired": "انتهت صلاحية رابط المشاركة",
        "sharing.notFound": "رابط المشاركة غير موجود",
        "sharing.invalidTitle": "رابط المشاركة غير صالح",
        "sharing.loading": "جارٍ تحميل المحادثة المشتركة...",
        "sharing.badge": "محادثة مشتركة",
        "sharing.expiresAt": "تنتهي الصلاحية: {{date}}",
        "sharing.readOnly": "هذه محادثة للقراءة فقط",
        "appName": "مساعد الذكاء الاصطناعي",
      }[key] ?? key),
  }),
}));

vi.mock("./ChatMessage", () => ({
  default: ({ text }) => <div>{text}</div>,
}));

describe("SharedConversationPage", () => {
  afterEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, "", "/share/test-token");
  });

  it("يطلب كلمة المرور للرابط المحمي ثم يعرض المحادثة بعد فتحه", async () => {
    getSharedConversation.mockRejectedValue({
      status: 401,
      detail: "share_password_required",
    });
    accessProtectedSharedConversation.mockResolvedValue({
      title: "محادثة محمية",
      created_at: "2026-09-21T10:00:00Z",
      expires_at: null,
      messages: [
        {
          role: "user",
          content: "رسالة سرية",
          created_at: "2026-09-21T10:00:00Z",
          sources: [],
        },
      ],
    });

    const user = userEvent.setup();
    render(<SharedConversationPage />);

    expect(await screen.findByText("هذا الرابط محمي بكلمة مرور")).toBeInTheDocument();

    await user.type(screen.getByPlaceholderText("كلمة المرور"), "SharePass123");
    await user.click(screen.getByRole("button", { name: "فتح الرابط" }));

    await waitFor(() => {
      expect(accessProtectedSharedConversation).toHaveBeenCalledWith(
        "test-token",
        "SharePass123"
      );
    });
    expect(await screen.findByText("رسالة سرية")).toBeInTheDocument();
  });

  it("يعرض خطأ كلمة المرور الخاطئة", async () => {
    getSharedConversation.mockRejectedValue({
      status: 401,
      detail: "share_password_required",
    });
    accessProtectedSharedConversation.mockRejectedValue({
      status: 401,
      detail: "invalid_share_password",
    });

    const user = userEvent.setup();
    render(<SharedConversationPage />);

    expect(await screen.findByText("هذا الرابط محمي بكلمة مرور")).toBeInTheDocument();
    await user.type(screen.getByPlaceholderText("كلمة المرور"), "WrongPass123");
    await user.click(screen.getByRole("button", { name: "فتح الرابط" }));

    expect(await screen.findByText("كلمة المرور غير صحيحة")).toBeInTheDocument();
  });

  it("يعرض المحادثة العامة بدون مطالبة بكلمة مرور", async () => {
    getSharedConversation.mockResolvedValue({
      title: "محادثة عامة",
      created_at: "2026-09-21T10:00:00Z",
      expires_at: null,
      messages: [
        {
          role: "assistant",
          content: "رد عام",
          created_at: "2026-09-21T10:00:00Z",
          sources: [],
        },
      ],
    });

    render(<SharedConversationPage />);

    expect(await screen.findByText("رد عام")).toBeInTheDocument();
    expect(accessProtectedSharedConversation).not.toHaveBeenCalled();
  });
});
