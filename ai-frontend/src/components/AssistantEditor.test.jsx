import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AssistantEditor from "./AssistantEditor";

const {
  listAssistantKnowledgeFiles,
  attachFileToAssistant,
  detachFileFromAssistant,
  listFiles,
  uploadFile,
  listAssistantVersions,
  restoreAssistantVersion,
  compareAssistantVersionWithCurrent,
  getAssistantAnalytics,
  getAssistantPublicSettings,
  enableAssistantPublicLink,
  rotateAssistantPublicLink,
  disableAssistantPublicLink,
} = vi.hoisted(() => ({
  listAssistantKnowledgeFiles: vi.fn(),
  attachFileToAssistant: vi.fn(),
  detachFileFromAssistant: vi.fn(),
  listFiles: vi.fn(),
  uploadFile: vi.fn(),
  listAssistantVersions: vi.fn(),
  restoreAssistantVersion: vi.fn(),
  compareAssistantVersionWithCurrent: vi.fn(),
  getAssistantAnalytics: vi.fn(),
  getAssistantPublicSettings: vi.fn(),
  enableAssistantPublicLink: vi.fn(),
  rotateAssistantPublicLink: vi.fn(),
  disableAssistantPublicLink: vi.fn(),
}));

vi.mock("../lib/assistantKnowledgeApi", () => ({
  listAssistantKnowledgeFiles,
  attachFileToAssistant,
  detachFileFromAssistant,
}));

vi.mock("../lib/filesApi", () => ({
  listFiles,
  uploadFile,
}));

vi.mock("../lib/assistantVersionsApi", () => ({
  listAssistantVersions,
  restoreAssistantVersion,
  compareAssistantVersionWithCurrent,
}));

vi.mock("../lib/assistantAnalyticsApi", () => ({
  getAssistantAnalytics,
}));

vi.mock("../lib/assistantsApi", () => ({
  getAssistantPublicSettings,
  enableAssistantPublicLink,
  rotateAssistantPublicLink,
  disableAssistantPublicLink,
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) =>
      ({
        "assistantEditor.createTitle": "إنشاء مساعد",
        "assistantEditor.editTitle": "تعديل المساعد",
        "assistantEditor.subtitle": "أنشئ مساعدًا مخصصًا",
        "assistantEditor.close": "إغلاق",
        "assistantEditor.nameLabel": "الاسم",
        "assistantEditor.namePlaceholder": "اسم المساعد",
        "assistantEditor.descriptionLabel": "الوصف",
        "assistantEditor.descriptionPlaceholder": "وصف اختياري",
        "assistantEditor.instructionsLabel": "التعليمات",
        "assistantEditor.instructionsPlaceholder": "اكتب تعليمات المساعد",
        "assistantEditor.requiredError": "أدخل الاسم والتعليمات",
        "assistantEditor.cancel": "إلغاء",
        "assistantEditor.saving": "جارٍ الحفظ...",
        "assistantEditor.save": "حفظ",
        "assistantEditor.knowledgeTitle": "ملفات المعرفة",
        "assistantEditor.knowledgeSubtitle": "المعرفة الدائمة",
        "assistantEditor.uploadFile": "رفع ملف",
        "assistantEditor.uploading": "جارٍ الرفع",
        "assistantEditor.noKnowledgeFiles": "لا توجد ملفات معرفة بعد.",
        "assistantEditor.knowledgeAttached": "مرفق",
        "assistantEditor.availableFiles": "ملفاتك المتاحة",
        "assistantEditor.attach": "إرفاق",
        "assistantEditor.detach": "إزالة",
        "assistantEditor.versionHistoryTitle": "سجل نسخ المساعد",
        "assistantEditor.versionHistorySubtitle": "استرجاع النسخ",
        "assistantEditor.noVersions": "لا توجد نسخ محفوظة بعد.",
        "assistantEditor.versionLabel": "الإصدار {{version}}",
        "assistantEditor.restore": "استرجاع",
        "assistantEditor.restoring": "جارٍ الاسترجاع...",
      "assistantEditor.compare": "مقارنة",
      "assistantEditor.comparing": "جارٍ المقارنة...",
      "assistantEditor.compareTitle": "مقارنة الإصدار {{version}}",
      "assistantEditor.compareChanged": "هناك تغييرات.",
      "assistantEditor.compareUnchanged": "لا توجد تغييرات.",
      "assistantEditor.compareNoDiff": "لا يوجد فرق.",
      "assistantEditor.compareError": "تعذر المقارنة.",
      "assistantEditor.closeCompare": "إغلاق المقارنة",
      "assistantEditor.analyticsTitle": "إحصائيات الاستخدام",
      "assistantEditor.analyticsSubtitle": "ملخص الاستخدام",
      "assistantEditor.analyticsConversations": "المحادثات",
      "assistantEditor.analyticsMessages": "الرسائل",
      "assistantEditor.analyticsUsers": "المستخدمون النشطون",
      "assistantEditor.analyticsLastUsed": "آخر استخدام",
      "assistantEditor.analyticsNever": "لم يُستخدم بعد",
      "assistantEditor.analyticsUnavailable": "تعذر تحميل إحصائيات الاستخدام",
      "assistantEditor.publicTitle": "الرابط العام",
      "assistantEditor.publicSubtitle": "شارك رابطًا آمنًا للمساعد.",
      "assistantEditor.publicEnabled": "الرابط العام مفعّل.",
      "assistantEditor.enablePublic": "تفعيل الرابط العام",
      "assistantEditor.copyPublic": "نسخ الرابط",
      "assistantEditor.rotatePublic": "تغيير الرابط",
      "assistantEditor.disablePublic": "إيقاف الرابط العام",
      "assistantEditor.rotatePublicConfirm": "تغيير الرابط؟",
      "assistantEditor.disablePublicConfirm": "إيقاف الرابط؟",
      "assistantEditor.copyPublicPrompt": "انسخ الرابط:",
      })[key] ?? key,
  }),
}));

describe("AssistantEditor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAssistantKnowledgeFiles.mockRejectedValue(new Error("knowledge unavailable"));
    listFiles.mockRejectedValue(new Error("files unavailable"));
    attachFileToAssistant.mockResolvedValue({});
    detachFileFromAssistant.mockResolvedValue(undefined);
    uploadFile.mockResolvedValue({ id: 10, original_filename: "linux.pdf" });
    listAssistantVersions.mockResolvedValue([]);
    compareAssistantVersionWithCurrent.mockResolvedValue({
      from_version: 1,
      current_version: 2,
      changed: true,
      diff: "@@ -1 +1 @@\n-old\n+new",
    });
    getAssistantPublicSettings.mockResolvedValue({
      is_public: false,
      public_token: null,
      public_url: null,
    });
    enableAssistantPublicLink.mockResolvedValue({
      is_public: true,
      public_token: "token",
      public_url: "https://example.com/public-assistant/token",
    });
    rotateAssistantPublicLink.mockResolvedValue({
      is_public: true,
      public_token: "token-2",
      public_url: "https://example.com/public-assistant/token-2",
    });
    disableAssistantPublicLink.mockResolvedValue({
      is_public: false,
      public_token: null,
      public_url: null,
    });
    getAssistantAnalytics.mockResolvedValue({
      assistant_id: 7,
      days: 30,
      conversation_count: 12,
      message_count: 48,
      active_user_count: 4,
      last_used_at: "2026-09-23T00:00:00Z",
    });
    restoreAssistantVersion.mockResolvedValue({
      id: 7,
      name: "مساعد قديم",
      description: "قديم",
      instructions: "تعليمات قديمة",
      version: 1,
    });
  });

  it("validates required fields", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<AssistantEditor onClose={vi.fn()} onSave={onSave} />);

    await user.click(screen.getByRole("button", { name: "حفظ" }));

    expect(screen.getByRole("alert")).toHaveTextContent("أدخل الاسم والتعليمات");
    expect(onSave).not.toHaveBeenCalled();
  });

  it("submits create form values", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<AssistantEditor onClose={vi.fn()} onSave={onSave} />);

    await user.type(screen.getByPlaceholderText("اسم المساعد"), "  مساعد الدراسة  ");
    await user.type(screen.getByPlaceholderText("وصف اختياري"), "  يساعدني في الدراسة  ");
    await user.type(
      screen.getByPlaceholderText("اكتب تعليمات المساعد"),
      "  اشرح باختصار وبأمثلة عملية.  "
    );

    await user.click(screen.getByRole("button", { name: "حفظ" }));

    expect(onSave).toHaveBeenCalledWith({
      name: "مساعد الدراسة",
      description: "يساعدني في الدراسة",
      instructions: "اشرح باختصار وبأمثلة عملية.",
    });
  });

  it("loads existing assistant data for editing and shows knowledge controls", () => {
    render(
      <AssistantEditor
        assistant={{
          id: 7,
          name: "مساعد البرمجة",
          description: "Python",
          instructions: "راجع الكود ثم اقترح تحسينات.",
        }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    expect(screen.getByDisplayValue("مساعد البرمجة")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Python")).toBeInTheDocument();
    expect(screen.getByDisplayValue("راجع الكود ثم اقترح تحسينات.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "تعديل المساعد" })).toBeInTheDocument();
    expect(screen.getByText("ملفات المعرفة")).toBeInTheDocument();
  });

  it("shows version history and can restore a previous version", async () => {
    listAssistantVersions.mockResolvedValue([
      {
        id: 1,
        version: 1,
        name: "مساعد قديم",
        description: "قديم",
        instructions: "تعليمات قديمة",
        created_at: "2026-09-22T10:00:00Z",
      },
    ]);
    const onRestored = vi.fn();
    const user = userEvent.setup();

    render(
      <AssistantEditor
        assistant={{
          id: 7,
          name: "مساعد حالي",
          description: "حالي",
          instructions: "تعليمات حالية",
        }}
        onClose={vi.fn()}
        onSave={vi.fn()}
        onRestored={onRestored}
      />
    );

    expect(await screen.findByText("سجل نسخ المساعد")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "استرجاع" }));

    expect(restoreAssistantVersion).toHaveBeenCalledWith(7, 1);
    expect(onRestored).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 7,
        instructions: "تعليمات قديمة",
      })
    );
  });

  it("compares a historical version with the current assistant", async () => {
    listAssistantVersions.mockResolvedValue([
      {
        id: 1,
        version: 1,
        name: "مساعد قديم",
        description: "قديم",
        instructions: "تعليمات قديمة",
        created_at: "2026-09-22T10:00:00Z",
      },
    ]);
    const user = userEvent.setup();

    render(
      <AssistantEditor
        assistant={{
          id: 7,
          name: "مساعد حالي",
          description: "حالي",
          instructions: "تعليمات حالية",
        }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    await user.click(await screen.findByRole("button", { name: "مقارنة" }));

    expect(compareAssistantVersionWithCurrent).toHaveBeenCalledWith(7, 1);
    expect(await screen.findByText("مقارنة الإصدار {{version}}")).toBeInTheDocument();
    expect(screen.getByText(/-old/)).toBeInTheDocument();
    expect(screen.getByText("+new", { exact: false })).toBeInTheDocument();
  });

  it("can enable a public assistant link", async () => {
    const user = userEvent.setup();
    enableAssistantPublicLink.mockResolvedValueOnce({
      is_public: true,
      public_token: "token",
      public_url: "https://example.com/public-assistant/token",
    });

    render(
      <AssistantEditor
        assistant={{
          id: 7,
          name: "مساعد عام",
          description: "عام",
          instructions: "تعليمات",
        }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    const button = await screen.findByRole("button", { name: "تفعيل الرابط العام" });
    await user.click(button);

    await waitFor(() =>
      expect(enableAssistantPublicLink).toHaveBeenCalledWith(7)
    );
    expect(await screen.findByDisplayValue("https://example.com/public-assistant/token")).toBeInTheDocument();
  });

  it("shows assistant usage analytics while editing", async () => {
    render(
      <AssistantEditor
        assistant={{
          id: 7,
          name: "مساعد حالي",
          description: "حالي",
          instructions: "تعليمات حالية",
        }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    expect(await screen.findByText("إحصائيات الاستخدام")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("48")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("does not show knowledge management while creating", () => {
    render(<AssistantEditor onClose={vi.fn()} onSave={vi.fn()} />);
    expect(screen.queryByText("ملفات المعرفة")).not.toBeInTheDocument();
  });
});
