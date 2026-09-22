import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import ProjectEditor from "./ProjectEditor";

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
        "projectEditor.cancel": "إلغاء",
        "projectEditor.saving": "جارٍ الحفظ...",
        "projectEditor.save": "حفظ",
      })[key] ?? key,
  }),
}));

describe("ProjectEditor", () => {
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
});
