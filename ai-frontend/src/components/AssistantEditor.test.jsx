import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import AssistantEditor from "./AssistantEditor";

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
      })[key] ?? key,
  }),
}));

describe("AssistantEditor", () => {
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

  it("loads existing assistant data for editing", () => {
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
  });
});
