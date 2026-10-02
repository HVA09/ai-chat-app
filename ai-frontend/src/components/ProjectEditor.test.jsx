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
  validateProject,
  getProjectPreviewPlan,
  buildProjectPreview,
  listProjectMembers,
  listWorkspaceMembers,
  addProjectMember,
  updateProjectMember,
  removeProjectMember,
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
  validateProject: vi.fn(),
  getProjectPreviewPlan: vi.fn(),
  buildProjectPreview: vi.fn(),
  listProjectMembers: vi.fn().mockResolvedValue([]),
  listWorkspaceMembers: vi.fn().mockResolvedValue([]),
  addProjectMember: vi.fn(),
  updateProjectMember: vi.fn(),
  removeProjectMember: vi.fn(),
}));

const { t } = vi.hoisted(() => ({
  t: (key, variables = {}) => {
    const value =
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
        "projectEditor.membersTitle": "أعضاء المشروع",
        "projectEditor.membersDescription": "تحكم فيمن يمكنه رؤية المشروع وتحريره وإدارته.",
        "projectEditor.membersLoading": "جارٍ تحميل أعضاء المشروع...",
        "projectEditor.membersEmpty": "لا يوجد أعضاء إضافيون في المشروع.",
        "projectEditor.membersYou": "أنت",
        "projectEditor.memberSelectPlaceholder": "اختر عضوًا من مساحة العمل",
        "projectEditor.memberRoleLabel": "دور {{email}}",
        "projectEditor.memberRoleAddLabel": "دور العضو الجديد",
        "projectEditor.memberAdd": "إضافة عضو",
        "projectEditor.memberSaving": "جارٍ الحفظ...",
        "projectEditor.memberRemove": "إزالة",
        "projectEditor.memberRemoveConfirm": "إزالة {{email}} من المشروع؟",
        "projectEditor.memberSaveError": "تعذر حفظ دور عضو المشروع.",
        "projectEditor.memberDeleteError": "تعذر إزالة عضو المشروع.",
        "projectEditor.membersWorkspaceOnly": "يمكن إضافة أعضاء موجودين داخل مساحة العمل فقط.",
        "projectEditor.roleOwner": "مالك المشروع",
        "projectEditor.roleViewer": "مشاهد",
        "projectEditor.roleEditor": "محرر",
        "projectEditor.roleManager": "مدير",
        "projectEditor.membersLoadError": "تعذر تحميل أعضاء المشروع.",
        "projectEditor.filesTitle": "ملفات المشروع",
        "projectEditor.filesDescription": "شجرة ملفات المصدر داخل المشروع.",
        "projectEditor.validate": "فحص المشروع",
        "projectEditor.validating": "جارٍ فحص المشروع...",
      "projectEditor.preview": "معاينة آمنة",
      "projectEditor.previewing": "جارٍ فتح المعاينة...",
      "projectEditor.previewTitle": "معاينة المشروع",
      "projectEditor.closePreview": "إغلاق المعاينة",
      "projectEditor.previewLoadError": "تعذر فتح معاينة المشروع.",
      "projectEditor.previewPlan": "خطة المعاينة",
      "projectEditor.previewPlanLoading": "جارٍ تحليل المعاينة...",
      "projectEditor.previewPlanTitle": "خطة المعاينة",
      "projectEditor.previewPlanStatus": "الحالة",
      "projectEditor.previewPlanEntrypoint": "نقطة الدخول",
      "projectEditor.previewPlanNone": "غير محددة",
      "projectEditor.previewPlanBuildDetected": "تم اكتشاف script للـbuild؛ التنفيذ يحتاج بيئة build معزولة.",
      "projectEditor.previewBuild": "بناء المعاينة",
      "projectEditor.previewBuildLoading": "جارٍ بناء المعاينة...",
      "projectEditor.previewBuildReady": "تم تجهيز artifact المعاينة",
      "projectEditor.previewBuildDescription": "تم البناء داخل Builder معزول. لن يتم تشغيل الملفات داخل هذه الصفحة مباشرة.",
      "projectEditor.previewBuildSize": "حجم artifact: {{size}} بايت",
      "projectEditor.previewBuildError": "تعذر بناء معاينة المشروع.",
        "projectEditor.validationReady": "نتيجة الفحص",
        "projectEditor.validationClean": "لا توجد أخطاء في الفحص.",
        "projectEditor.validationSummary": "{{errors}} أخطاء، {{warnings}} تحذيرات — {{count}} ملف",
        "projectEditor.validationLoadError": "تعذر فحص المشروع.",
        "projectEditor.validationError": "خطأ",
        "projectEditor.validationWarning": "تحذير",
        "projectEditor.validationInfo": "معلومة",
        "projectEditor.filesEmpty": "لا توجد ملفات مصدر بعد.",
        "projectEditor.fileNew": "ملف جديد",
        "projectEditor.filePathLabel": "مسار الملف",
        "projectEditor.filePathPlaceholder": "src/App.jsx",
        "projectEditor.fileContentLabel": "محتوى الملف",
        "projectEditor.fileContentPlaceholder": "اكتب كود أو نص الملف هنا...",
        "projectEditor.fileLoading": "جارٍ تحميل الملف...",
        "projectEditor.fileSaving": "جارٍ حفظ الملف...",
        "projectEditor.fileCreate": "إنشاء الملف",
        "projectEditor.fileSave": "حفظ الملف",
        "projectEditor.fileDeleting": "جارٍ حذف الملف...",
        "projectEditor.fileDelete": "حذف الملف",
        "projectEditor.filePathRequired": "أدخل مسار الملف.",
        "projectEditor.fileLoadError": "تعذر تحميل ملفات المشروع.",
        "projectEditor.fileSaveError": "تعذر حفظ ملف المشروع.",
        "projectEditor.fileDeleteError": "تعذر حذف ملف المشروع.",
        "projectEditor.fileDeleteConfirm": "حذف الملف؟",
        "projectEditor.cancel": "إلغاء",
        "projectEditor.saving": "جارٍ الحفظ...",
        "projectEditor.save": "حفظ",
      }[key] ?? key);
    return value.replace(/{{\s*(\w+)\s*}}/g, (_, name) =>
      String(variables[name] ?? "")
    );
  },
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

vi.mock("../lib/projectValidationApi", () => ({
  validateProject,
  getProjectPreviewPlan,
  buildProjectPreview,
}));

vi.mock("../lib/projectMembersApi", () => ({
  listProjectMembers,
  addProjectMember,
  updateProjectMember,
  removeProjectMember,
}));

vi.mock("../lib/workspaceMembersApi", () => ({
  listWorkspaceMembers,
}));

describe("ProjectEditor", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("loads project members and lets a project manager add and change members", async () => {
    listProjectMemories.mockResolvedValue([]);
    listProjectFiles.mockResolvedValue([]);
    listProjectMembers.mockResolvedValue([
      {
        id: null,
        project_id: 3,
        user_id: 1,
        email: "owner@example.com",
        full_name: "Owner",
        role: "manager",
        is_owner: true,
      },
      {
        id: 10,
        project_id: 3,
        user_id: 2,
        email: "viewer@example.com",
        full_name: "Viewer",
        role: "viewer",
        is_owner: false,
      },
    ]);
    listWorkspaceMembers.mockResolvedValue([
      {
        id: 1,
        user_id: 1,
        email: "owner@example.com",
        full_name: "Owner",
        role: "owner",
      },
      {
        id: 2,
        user_id: 2,
        email: "viewer@example.com",
        full_name: "Viewer",
        role: "member",
      },
      {
        id: 3,
        user_id: 3,
        email: "editor@example.com",
        full_name: "Editor",
        role: "member",
      },
    ]);
    addProjectMember.mockResolvedValue({
      id: 11,
      project_id: 3,
      user_id: 3,
      email: "editor@example.com",
      full_name: "Editor",
      role: "editor",
      is_owner: false,
    });
    updateProjectMember.mockResolvedValue({
      id: 10,
      project_id: 3,
      user_id: 2,
      email: "viewer@example.com",
      full_name: "Viewer",
      role: "editor",
      is_owner: false,
    });

    const user = userEvent.setup();
    render(
      <ProjectEditor
        project={{
          id: 3,
          workspace_id: 9,
          owner_id: 1,
          name: "Demo",
          description: null,
          instructions: null,
        }}
        currentUserId={1}
        workspaceRole="owner"
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    expect(await screen.findByText("أعضاء المشروع")).toBeInTheDocument();
    expect(screen.getByText("viewer@example.com")).toBeInTheDocument();

    await user.selectOptions(
      screen.getByRole("combobox", { name: "دور viewer@example.com" }),
      "editor"
    );
    expect(updateProjectMember).toHaveBeenCalledWith(3, 10, "editor");

    await user.selectOptions(
      screen.getByRole("combobox", { name: "اختر عضوًا من مساحة العمل" }),
      "3"
    );
    await user.selectOptions(
      screen.getByRole("combobox", { name: "دور العضو الجديد" }),
      "editor"
    );
    await user.click(screen.getByRole("button", { name: "إضافة عضو" }));

    expect(addProjectMember).toHaveBeenCalledWith(3, "3", "editor");
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

  it("runs read-only project validation and shows issues", async () => {
    listProjectMemories.mockResolvedValue([]);
    listProjectFiles.mockResolvedValue([]);
    validateProject.mockResolvedValue({
      project_id: 3,
      project_kind: "javascript",
      files_count: 2,
      errors: 1,
      warnings: 1,
      checks: [
        {
          level: "error",
          code: "invalid_package_json",
          message: "package.json غير صالح",
          path: "package.json",
        },
        {
          level: "warning",
          code: "secret_file_name",
          message: "لا تضع أسرارًا حقيقية",
          path: ".env",
        },
      ],
    });

    const user = userEvent.setup();
    render(
      <ProjectEditor
        project={{ id: 3, name: "Demo", description: null, instructions: null }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    await user.click(await screen.findByRole("button", { name: "فحص المشروع" }));

    expect(validateProject).toHaveBeenCalledWith(3);
    expect(await screen.findByText("package.json غير صالح")).toBeInTheDocument();
    expect(screen.getByText("لا تضع أسرارًا حقيقية")).toBeInTheDocument();
    expect(screen.getByText(/1 أخطاء، 1 تحذيرات/)).toBeInTheDocument();
  });

  it("opens index.html in a sandboxed preview without script permission", async () => {
    listProjectMemories.mockResolvedValue([]);
    listProjectFiles.mockResolvedValue([
      { id: 20, project_id: 3, path: "index.html", content_length: 34 },
    ]);
    getProjectFile.mockResolvedValue({
      id: 20,
      project_id: 3,
      path: "index.html",
      content: "<html><body><h1>Hello</h1></body></html>",
    });

    const user = userEvent.setup();
    render(
      <ProjectEditor
        project={{ id: 3, name: "Demo", description: null, instructions: null }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    await user.click(await screen.findByRole("button", { name: "معاينة آمنة" }));

    const frame = await screen.findByTitle("معاينة المشروع");
    expect(getProjectFile).toHaveBeenCalledWith(3, 20);
    expect(frame).toHaveAttribute("sandbox", "");
    expect(frame).toHaveAttribute(
      "srcdoc",
      "<html><body><h1>Hello</h1></body></html>"
    );
  });





  it("builds a JavaScript project preview and shows artifact metadata", async () => {
    listProjectMemories.mockResolvedValue([]);
    listProjectFiles.mockResolvedValue([
      { id: 30, project_id: 3, path: "package.json", content_length: 80 },
    ]);
    getProjectPreviewPlan.mockResolvedValue({
      project_id: 3,
      project_kind: "javascript",
      strategy: "javascript-build",
      status: "build-required",
      entrypoint: "package.json",
      build_command_detected: true,
      artifact_root: null,
      message: "المشروع يحتاج build معزول قبل المعاينة.",
    });
    buildProjectPreview.mockResolvedValue({
      entrypoint: "index.html",
      artifact_base64: "YQ==",
      artifact_size_bytes: 1,
      preview_url:
        "https://api.example.com/projects/3/preview-artifacts/abc/token/index.html",
      preview_expires_at: 9999999999,
    });

    const user = userEvent.setup();
    render(
      <ProjectEditor
        project={{ id: 3, name: "Demo", description: null, instructions: null }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    await user.click(await screen.findByRole("button", { name: "خطة المعاينة" }));
    await user.click(await screen.findByRole("button", { name: "بناء المعاينة" }));

    expect(buildProjectPreview).toHaveBeenCalledWith(3);
    expect(await screen.findByText("تم تجهيز artifact المعاينة")).toBeInTheDocument();
    expect(screen.getByText("index.html")).toBeInTheDocument();
    expect(screen.getByText("حجم artifact: 1 بايت")).toBeInTheDocument();
  });

  it("loads and shows the isolated preview strategy plan", async () => {
    listProjectMemories.mockResolvedValue([]);
    listProjectFiles.mockResolvedValue([
      { id: 30, project_id: 3, path: "package.json", content_length: 80 },
    ]);
    getProjectPreviewPlan.mockResolvedValue({
      project_id: 3,
      project_kind: "javascript",
      strategy: "javascript-build",
      status: "build-required",
      entrypoint: "package.json",
      build_command_detected: true,
      artifact_root: null,
      message: "المشروع يحتاج build معزول قبل المعاينة.",
    });

    const user = userEvent.setup();
    render(
      <ProjectEditor
        project={{ id: 3, name: "Demo", description: null, instructions: null }}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );

    await user.click(await screen.findByRole("button", { name: "خطة المعاينة" }));

    expect(getProjectPreviewPlan).toHaveBeenCalledWith(3);
    expect(await screen.findByText("المشروع يحتاج build معزول قبل المعاينة.")).toBeInTheDocument();
    expect(screen.getByText("javascript-build")).toBeInTheDocument();
    expect(screen.getByText("تم اكتشاف script للـbuild؛ التنفيذ يحتاج بيئة build معزولة.")).toBeInTheDocument();
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
    listProjectFiles.mockImplementation(() => {
      if (createProjectFile.mock.calls.length > 0) {
        return Promise.resolve([
          { id: 20, project_id: 3, path: "src/main.jsx", content_length: 19 },
          { id: 21, project_id: 3, path: "README.md", content_length: 5 },
        ]);
      }
      if (updateProjectFile.mock.calls.length > 0) {
        return Promise.resolve([
          { id: 20, project_id: 3, path: "src/main.jsx", content_length: 19 },
        ]);
      }
      return Promise.resolve([
        { id: 20, project_id: 3, path: "src/App.jsx", content_length: 22 },
      ]);
    });
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

    vi.spyOn(window, "confirm").mockReturnValue(true);
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
