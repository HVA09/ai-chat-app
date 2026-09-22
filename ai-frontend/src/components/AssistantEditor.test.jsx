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
} = vi.hoisted(() => ({
  listAssistantKnowledgeFiles: vi.fn(),
  attachFileToAssistant: vi.fn(),
  detachFileFromAssistant: vi.fn(),
  listFiles: vi.fn(),
  uploadFile: vi.fn(),
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
      })[key] ?? key,
  }),
}));

describe("AssistantEditor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAssistantKnowledgeFiles.mockResolvedValue([]);
    listFiles.mockResolvedValue([
      { id: 10, original_filename: "linux.pdf" },
    ]);
    attachFileToAssistant.mockResolvedValue({});
    detachFileFromAssistant.mockResolvedValue(undefined);
    uploadFile.mockResolvedValue({
      id: 10,
      original_filename: "linux.pdf",
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

  it("loads existing assistant data for editing", async () => {
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
    await waitFor(() => expect(screen.getByText("linux.pdf")).toBeInTheDocument());
  });

  it("can attach an available personal file", async () => {
    const user = userEvent.setup();

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

    const attachButtons = await screen.findAllByText("إرفاق");
    await user.click(attachButtons[0]);

    await waitFor(() => {
      expect(attachFileToAssistant).toHaveBeenCalledWith(7, 10);
    });
  });

  it("does not show knowledge management while creating", () => {
    render(<AssistantEditor onClose={vi.fn()} onSave={vi.fn()} />);
    expect(screen.queryByText("ملفات المعرفة")).not.toBeInTheDocument();
  });
});
