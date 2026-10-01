import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import ProjectEditor from "./ProjectEditor";

const {
  listProjectMemories,
  createProjectMemory,
  updateProjectMemory,
  deleteProjectMemory,
  listProjectFiles,
  getProjectFile,
  createProjectFile,
  updateProjectFile,
  deleteProjectFile,
} = vi.hoisted(() => ({
  listProjectMemories: vi.fn(),
  createProjectMemory: vi.fn(),
  updateProjectMemory: vi.fn(),
  deleteProjectMemory: vi.fn(),
  listProjectFiles: vi.fn().mockResolvedValue([]),
  getProjectFile: vi.fn(),
  createProjectFile: vi.fn(),
  updateProjectFile: vi.fn(),
  deleteProjectFile: vi.fn(),
}));

const { t } = vi.hoisted(() => ({
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
      "projectEditor.assistantLabel": "المساعد الافتراضي",
      "projectEditor.noDefaultAssistant": "بدون مساعد افتراضي",
      "projectEditor.assistantHint": "سيُستخدم تلقائيًا للمحادثات الجديدة داخل المشروع.",
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
    }[key] ?? key),
}));


vi.mock("../lib/errors", () => ({
  getErrorMessage: vi.fn((error, fallback) => error?.response?.data?.detail || fallback),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t }),
}));

vi.mock("../lib/projectMemoriesApi", () => ({
  listProjectMemories,
  createProjectMemory,
  updateProjectMemory,
  deleteProjectMemory,
}));

vi.mock("../lib/projectFilesApi", () => ({
  listProjectFiles,
  getProjectFile,
  createProjectFile,
  updateProjectFile,
  deleteProjectFile,
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
      assistant_id: null,
    });
  });

  it("selects a default assistant and restores it for an existing project", async () => {
    listProjectMemories.mockResolvedValue([]);
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <ProjectEditor
        assistants={[
          { id: 4, name: "مساعد الدراسة" },
          { id: 7, name: "مساعد البرمجة" },
        ]}
        project={{
          id: 3,
          name: "Python",
          description: "تعلم البرمجة",
          instructions: "استخدم أمثلة عملية.",
          assistant_id: 7,
        }}
        onClose={vi.fn()}
        onSave={onSave}
      />
    );

    const select = screen.getByRole("combobox");
    expect(select).toHaveValue("7");

    await user.selectOptions(select, "4");
    await user.click(screen.getByRole("button", { name: "حفظ" }));

    expect(onSave).toHaveBeenCalledWith({
      name: "Python",
      description: "تعلم البرمجة",
      instructions: "استخدم أمثلة عملية.",
      assistant_id: 4,
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
  it("loads, edits, creates, and deletes project source files", async () => {
    listProjectMemories.mockResolvedValue([]);
    listProjectFiles.mockResolvedValue([
      { id: 20, project_id: 3, path: "src/App.jsx", content_length: 22 },
    ]);
    getProjectFile.mockResolvedValue({
      id: 20,
      project_id: 3,
      path: "src/App.jsx",
      content: "export default App;",
    });
    updateProjectFile.mockResolvedValue({
      id: 20,
      project_id: 3,
      path: "src/main.jsx",
      content: "export default Main;",
    });
    createProjectFile.mockResolvedValue({
      id: 21,
      project_id: 3,
      path: "README.md",
      content: "# App",
    });
    deleteProjectFile.mockResolvedValue(undefined);

    const user = userEvent.setup();
    render(
      <ProjectEditor
        project={{ id: 3, name: "App", description: null, instructions: null }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    expect(await screen.findByText("src/App.jsx")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /src\/App\.jsx/ }));
    const fileContentEditor = await screen.findByDisplayValue("export default App;");
    expect(fileContentEditor).toBeInTheDocument();

    const filePathEditor = screen.getByDisplayValue("src/App.jsx");
    await user.clear(filePathEditor);
    await user.type(filePathEditor, "src/main.jsx");
    await user.clear(fileContentEditor);
    await user.type(fileContentEditor, "export default Main;");
    await user.click(screen.getByRole("button", { name: "حفظ الملف" }));

    expect(updateProjectFile).toHaveBeenCalledWith(
      3,
      20,
      "src/main.jsx",
      "export default Main;"
    );

    await user.click(screen.getByRole("button", { name: "ملف جديد" }));
    await user.type(screen.getByPlaceholderText("src/App.jsx"), "README.md");
    await user.type(screen.getByPlaceholderText("اكتب كود أو نص الملف هنا..."), "# App");
    await user.click(screen.getByRole("button", { name: "إنشاء الملف" }));

    expect(createProjectFile).toHaveBeenCalledWith(3, "README.md", "# App");

    await user.click(screen.getByRole("button", { name: "حذف الملف" }));
    expect(deleteProjectFile).toHaveBeenCalledWith(3, 21);
  });

  it("shows a global toast when project memory loading fails", async () => {
    listProjectMemories.mockRejectedValueOnce({
      response: { data: { detail: "Memory load denied" } },
    });
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    render(
      <ProjectEditor
        project={{ id: 3, name: "Python" }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(
        dispatchSpy.mock.calls.some(
          ([event]) =>
            event.type === "app:toast" &&
            event.detail?.message === "Memory load denied" &&
            event.detail?.type === "error"
        )
      ).toBe(true);
    });

    expect(screen.queryByText("Memory load denied")).not.toBeInTheDocument();
    dispatchSpy.mockRestore();
  });

  it("shows a global toast when creating project memory fails", async () => {
    listProjectMemories.mockResolvedValue([]);
    createProjectMemory.mockRejectedValueOnce({
      response: { data: { detail: "Memory create denied" } },
    });
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    const user = userEvent.setup();

    render(
      <ProjectEditor
        project={{ id: 3, name: "Python" }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    await user.type(screen.getByPlaceholderText("ذاكرة"), "ذاكرة جديدة");
    await user.click(screen.getByRole("button", { name: "إضافة ذاكرة" }));

    await waitFor(() => {
      expect(
        dispatchSpy.mock.calls.some(
          ([event]) =>
            event.type === "app:toast" &&
            event.detail?.message === "Memory create denied" &&
            event.detail?.type === "error"
        )
      ).toBe(true);
    });

    expect(screen.queryByText("Memory create denied")).not.toBeInTheDocument();
    dispatchSpy.mockRestore();
  });

  it("shows a global toast when updating project memory fails", async () => {
    listProjectMemories.mockResolvedValue([{ id: 10, content: "Old memory" }]);
    updateProjectMemory.mockRejectedValueOnce({
      response: { data: { detail: "Memory update denied" } },
    });
    vi.spyOn(window, "prompt").mockReturnValue("New memory");
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    const user = userEvent.setup();

    render(
      <ProjectEditor
        project={{ id: 3, name: "Python" }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    await user.click(await screen.findByRole("button", { name: "تعديل" }));

    await waitFor(() => {
      expect(
        dispatchSpy.mock.calls.some(
          ([event]) =>
            event.type === "app:toast" &&
            event.detail?.message === "Memory update denied" &&
            event.detail?.type === "error"
        )
      ).toBe(true);
    });

    expect(screen.queryByText("Memory update denied")).not.toBeInTheDocument();
    dispatchSpy.mockRestore();
  });

  it("shows a global toast when deleting project memory fails", async () => {
    listProjectMemories.mockResolvedValue([{ id: 10, content: "Old memory" }]);
    deleteProjectMemory.mockRejectedValueOnce({
      response: { data: { detail: "Memory delete denied" } },
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    const user = userEvent.setup();

    render(
      <ProjectEditor
        project={{ id: 3, name: "Python" }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    await user.click(await screen.findByRole("button", { name: "حذف" }));

    await waitFor(() => {
      expect(
        dispatchSpy.mock.calls.some(
          ([event]) =>
            event.type === "app:toast" &&
            event.detail?.message === "Memory delete denied" &&
            event.detail?.type === "error"
        )
      ).toBe(true);
    });

    expect(screen.queryByText("Memory delete denied")).not.toBeInTheDocument();
    dispatchSpy.mockRestore();
  });

});
