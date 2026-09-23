import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AccountSettings from "./AccountSettings";
import { listSessions } from "../lib/sessionsApi";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) =>
      ({
        "account.title": "الحساب",
        "account.conversationTitlesSection": "عناوين المحادثات",
        "account.autoGenerateTitles": "توليد عنوان تلقائي",
        "account.autoGenerateTitlesDescription": "وصف",
        "account.conversationSummariesSection": "التلخيص التلقائي للمحادثات",
        "account.autoGenerateSummaries": "إنشاء ملخصات تلقائيًا للمحادثات الطويلة",
        "account.autoGenerateSummariesDescription": "وصف التلخيص",
        "account.profileSection": "الملف الشخصي",
        "account.namePlaceholder": "الاسم",
        "account.avatarPlaceholder": "الصورة",
        "account.save": "حفظ",
        "account.memorySection": "الذاكرة",
        "account.memoryDescription": "وصف",
        "account.memoryPlaceholder": "مثال",
        "account.memoryAdd": "إضافة",
        "account.changePasswordSection": "كلمة المرور",
        "account.emailSection": "البريد",
        "account.twoFASection": "2FA",
        "account.deleteAccountTitle": "حذف",
        "account.dataExportSection": "تصدير",
        "account.dataExportDescription": "وصف",
        "account.exportData": "تصدير بياناتي",
        "account.dataExported": "تم",
        "account.sessionsSection": "الجلسات",
        "account.sessionsDescription": "وصف",
        "account.noSessions": "لا توجد جلسات",
        "account.unknownDevice": "جهاز",
        "account.currentSession": "الحالية",
        "account.revokeSession": "إلغاء",
        "account.revokeAllSessions": "إلغاء الكل",
        "account.sessionRevokeConfirm": "متأكد؟",
        "account.sessionRevokeAllConfirm": "متأكد؟",
        "account.sessionRevoked": "تم",
        "account.sessionsRevoked": "تم",
        "account.sessionsLoadError": "خطأ",
        "account.apiKeysSection": "API",
        "account.apiKeysDescription": "API",
        "account.genericError": "خطأ",
        "account.memoryLoadError": "ذاكرة",
        "account.apiKeysLoadError": "API",
      })[key] ?? key,
  }),
}));

vi.mock("../lib/authApi", () => ({
  requestEmailVerification: vi.fn().mockResolvedValue({ detail: "ok" }),
  setupTwoFactor: vi.fn().mockResolvedValue({ qr_code_base64: "", secret: "test" }),
  enableTwoFactor: vi.fn().mockResolvedValue({}),
  disableTwoFactor: vi.fn().mockResolvedValue({}),
}));

vi.mock("../lib/usersApi", () => ({
  updateProfile: vi.fn().mockResolvedValue({}),
  changePassword: vi.fn().mockResolvedValue({}),
  deleteAccount: vi.fn().mockResolvedValue({}),
  exportAccountData: vi.fn().mockResolvedValue({}),
}));

vi.mock("../lib/memoriesApi", () => ({
  listMemories: vi.fn().mockResolvedValue([]),
  createMemory: vi.fn().mockResolvedValue({}),
  updateMemory: vi.fn().mockResolvedValue({}),
  deleteMemory: vi.fn().mockResolvedValue({}),
}));

vi.mock("../lib/sessionsApi", () => ({
  listSessions: vi.fn().mockResolvedValue([]),
  revokeSession: vi.fn().mockResolvedValue({}),
  revokeAllSessions: vi.fn().mockResolvedValue({}),
}));

vi.mock("../lib/apiKeysApi", () => ({
  listApiKeys: vi.fn().mockResolvedValue([]),
  createApiKey: vi.fn().mockResolvedValue({}),
  revokeApiKey: vi.fn().mockResolvedValue({}),
  getApiKeyUsage: vi.fn().mockResolvedValue(null),
}));

vi.mock("../lib/errors", () => ({
  getErrorMessage: vi.fn((err, fallback) => fallback),
}));

describe("AccountSettings", () => {
  beforeEach(() => {
    window.localStorage.clear();
    listSessions.mockResolvedValue([]);
  });

  it("toggles the automatic summary preference and persists it locally", async () => {
    const user = userEvent.setup();
    const onAutoGenerateSummariesChanged = vi.fn();

    render(
      <AccountSettings
        user={{
          full_name: "",
          avatar_url: "",
          is_email_verified: true,
          is_2fa_enabled: false,
        }}
        autoGenerateTitles={false}
        onAutoGenerateTitlesChanged={vi.fn()}
        autoGenerateSummaries={false}
        onAutoGenerateSummariesChanged={onAutoGenerateSummariesChanged}
        onClose={vi.fn()}
        onUserUpdated={vi.fn()}
        onAccountDeleted={vi.fn()}
      />
    );

    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes).toHaveLength(2);

    await user.click(checkboxes[1]);

    expect(onAutoGenerateSummariesChanged).toHaveBeenCalledWith(true);
    expect(window.localStorage.getItem("ai-chat-auto-summary")).toBe("true");
  });


  it("exports account data", async () => {
    const user = userEvent.setup();
    const { exportAccountData } = await import("../lib/usersApi");

    render(
      <AccountSettings
        user={{
          full_name: "",
          avatar_url: "",
          is_email_verified: true,
          is_2fa_enabled: false,
        }}
        autoGenerateTitles={false}
        onAutoGenerateTitlesChanged={vi.fn()}
        autoGenerateSummaries={false}
        onAutoGenerateSummariesChanged={vi.fn()}
        onClose={vi.fn()}
        onUserUpdated={vi.fn()}
        onAccountDeleted={vi.fn()}
      />
    );

    await user.click(screen.getByText("تصدير بياناتي"));
    expect(exportAccountData).toHaveBeenCalledTimes(1);
  });
});


  it("renders active login sessions", async () => {
    listSessions.mockResolvedValueOnce([
      {
        id: 7,
        user_agent: "Chrome on Android",
        ip_address: "10.0.0.1",
        last_used_at: "2026-09-23T10:00:00Z",
        expires_at: "2026-09-30T10:00:00Z",
        created_at: "2026-09-23T09:00:00Z",
        is_current: true,
      },
    ]);

    render(
      <AccountSettings
        user={{
          full_name: "",
          avatar_url: "",
          is_email_verified: true,
          is_2fa_enabled: false,
        }}
        autoGenerateTitles={false}
        onAutoGenerateTitlesChanged={vi.fn()}
        autoGenerateSummaries={false}
        onAutoGenerateSummariesChanged={vi.fn()}
        onClose={vi.fn()}
        onUserUpdated={vi.fn()}
        onAccountDeleted={vi.fn()}
      />
    );

    expect(await screen.findByText("Chrome on Android")).toBeInTheDocument();
    expect(screen.getByText("الحالية")).toBeInTheDocument();
  });
