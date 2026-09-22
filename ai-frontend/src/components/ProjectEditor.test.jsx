import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import ProjectEditor from "./ProjectEditor";

const {
  listProjectMemories,
  createProjectMemory,
  updateProjectMemory,
  deleteProjectMemory,
} = vi.hoisted(() => ({
  listProjectMemories: vi.fn(),
  createProjectMemory: vi.fn(),
  updateProjectMemory: vi.fn(),
  deleteProjectMemory: vi.fn(),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) =>
      ({
        "projectEditor.createTitle": "إنشاء مشروع",
        "projectEditor.editTitle": "تعديل المشروع",
        "projectEditor.subtitle": "نظّم المشروع وحدد سلوكه الدائم للمساعد",
        "projectEditor.close": "إغلاق",
        "projectEditor.nameLabel": "الاسم",
        "projectEditor.namePlaceholder": "اسم المشروع",
        "projectEditor.descriptionLabel": "الوصف",
        "projectEditor.descriptionPlaceholder": "وصف اختياري",
        "projectEditor.instructionsLabel": "تعليمات المشروع",
        "projectEditor.instructionsPlaceholder": "كيف يجب أن يتعامل المساعد مع هذا المشروع؟",
        "projectEditor.requiredError": "أدخل اسم المشروع",
        "projectEditor.memoryTitle": "ذاكرة المشروع",
        "projectEditor.memoryDescription": "ذاكرة مشتركة",
        "projectEditor.memoryPlaceholder": "ذاكرة",
        "projectEditor.memoryAdd": "إضافة ذاكرة",
        "projectEditor.memorySaving": "جارٍ الحفظ...",
        "projectEditor.memoryLoading": "جارٍ تحميل الذاكرة...",
        "projectEditor.memoryEmpty": "لا توجد ذكريات محفوظة لهذا المشروع.",
        "projectEditor.memoryEdit": "تعديل",
        "projectEditor.memoryDelete": "حذف",
        "projectEditor.memoryEditPrompt": "عدّل ذاكرة المشروع:",
        "projectEditor.memoryDeleteConfirm": "حذف ذاكرة المشروع؟",
        "projectEditor.memoryLoadError": "تعذر تحميل ذاكرة المشروع",
        "projectEditor.memorySaveError": "تعذر حفظ ذاكرة المشروع",
        "projectEditor.memoryDeleteError": "تعذر حذف ذاكرة المشروع",
        "projectEditor.cancel": "إلغاء",
        "projectEditor.saving": "جارٍ الحفظ...",
        "projectEditor.save": "حفظ",
      })[key] ?? key,
  }),
}));

vi.mock("../lib/projectMemoriesApi", () => ({
  listProjectMemories,
  createProjectMemory,
  updateProjectMemory,
  deleteProjectMemory,
}));

describe("ProjectEditor", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("validates the project name", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<ProjectEditor onClose={vi.fn()} onSave={onSave} />);

    await user.click(screen.getByRole("button", { name: "حفظ" }));

    expect(screen.getByRole("alert")).toHaveTextContent("أدخل اسم المشروع");
    expect(onSave).not.toHaveBeenCalled();
  });

  it("submits project instructions", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<ProjectEditor onClose={vi.fn()} onSave={onSave} />);

    await user.type(screen.getByPlaceholderText("اسم المشروع"), "  Python  ");
    await user.type(screen.getByPlaceholderText("وصف اختياري"), "  تعلم بايثون  ");
    await user.type(
      screen.getByPlaceholderText("كيف يجب أن يتعامل المساعد مع هذا المشروع؟"),
      "  اشرح بالعربية وبخطوات بسيطة.  "
    );

    await user.click(screen.getByRole("button", { name: "حفظ" }));

    expect(onSave).toHaveBeenCalledWith({
      name: "Python",
      description: "تعلم بايثون",
      instructions: "اشرح بالعربية وبخطوات بسيطة.",
    });
  });

  it("loads existing project values", () => {
    listProjectMemories.mockResolvedValue([]);
    render(
      <ProjectEditor
        project={{
          id: 3,
          name: "Python",
          description: "تعلم البرمجة",
          instructions: "استخدم أمثلة عملية.",
        }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    expect(screen.getByDisplayValue("Python")).toBeInTheDocument();
    expect(screen.getByDisplayValue("تعلم البرمجة")).toBeInTheDocument();
    expect(screen.getByDisplayValue("استخدم أمثلة عملية.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "تعديل المشروع" })).toBeInTheDocument();
  });

  it("loads and creates project memory", async () => {
    listProjectMemories.mockResolvedValue([
      {
        id: 10,
        project_id: 3,
        created_by_user_id: 1,
        content: "استخدم أمثلة عملية",
        created_at: "2026-09-22T10:00:00Z",
        updated_at: "2026-09-22T10:00:00Z",
      },
    ]);
    createProjectMemory.mockResolvedValue({
      id: 11,
      project_id: 3,
      created_by_user_id: 1,
      content: "يفضل المستخدم العربية",
      created_at: "2026-09-22T11:00:00Z",
      updated_at: "2026-09-22T11:00:00Z",
    });

    const user = userEvent.setup();
    render(
      <ProjectEditor
        project={{ id: 3, name: "Python", description: null, instructions: null }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    expect(await screen.findByText("استخدم أمثلة عملية")).toBeInTheDocument();

    await user.type(screen.getByPlaceholderText("ذاكرة"), "يفضل المستخدم العربية");
    await user.click(screen.getByRole("button", { name: "إضافة ذاكرة" }));

    expect(createProjectMemory).toHaveBeenCalledWith(3, "يفضل المستخدم العربية");
    expect(await screen.findByText("يفضل المستخدم العربية")).toBeInTheDocument();
  });

  it("edits and deletes project memory", async () => {
    listProjectMemories.mockResolvedValue([
      {
        id: 10,
        project_id: 3,
        created_by_user_id: 1,
        content: "الذاكرة القديمة",
        created_at: "2026-09-22T10:00:00Z",
        updated_at: "2026-09-22T10:00:00Z",
      },
    ]);
    updateProjectMemory.mockResolvedValue({
      id: 10,
      project_id: 3,
      created_by_user_id: 1,
      content: "الذاكرة الجديدة",
      created_at: "2026-09-22T10:00:00Z",
      updated_at: "2026-09-22T12:00:00Z",
    });
    deleteProjectMemory.mockResolvedValue(undefined);
    vi.spyOn(window, "prompt").mockReturnValue("الذاكرة الجديدة");
    vi.spyOn(window, "confirm").mockReturnValue(true);

    const user = userEvent.setup();
    render(
      <ProjectEditor
        project={{ id: 3, name: "Python", description: null, instructions: null }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    expect(await screen.findByText("الذاكرة القديمة")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "تعديل" }));
    await waitFor(() =>
      expect(updateProjectMemory).toHaveBeenCalledWith(3, 10, "الذاكرة الجديدة")
    );

    expect(await screen.findByText("الذاكرة الجديدة")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "حذف" }));
    expect(deleteProjectMemory).toHaveBeenCalledWith(3, 10);
    await waitFor(() =>
      expect(screen.queryByText("الذاكرة الجديدة")).not.toBeInTheDocument()
    );
  });
});
