import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import OnboardingModal from "./OnboardingModal";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key, values = {}) => {
      const map = {
        "onboarding.title": "مرحبًا بك",
        "onboarding.close": "إغلاق",
        "onboarding.skip": "تخطي",
        "onboarding.back": "السابق",
        "onboarding.next": "التالي",
        "onboarding.goToStep": "الخطوة {{step}}",
        "onboarding.stepCounter": "الخطوة {{current}} من {{total}}",
        "onboarding.steps.chat.title": "ابدأ محادثتك",
        "onboarding.steps.chat.description": "أرسل سؤالك وابدأ مباشرة.",
        "onboarding.steps.chat.action": "ابدأ الآن",
        "onboarding.steps.organize.title": "نظّم محادثاتك",
        "onboarding.steps.organize.description": "استخدم المجلدات والمشاريع لحفظ عملك مرتبًا.",
        "onboarding.steps.organize.action": "افتح الحساب",
        "onboarding.steps.knowledge.title": "استخدم ملفاتك",
        "onboarding.steps.knowledge.description": "ارفع الملفات واستفد من البحث والمصادر.",
        "onboarding.steps.knowledge.action": "افتح الملفات",
      };
      let value = map[key] ?? key;
      Object.entries(values).forEach(([name, replacement]) => {
        value = value.replaceAll(`{{${name}}}`, String(replacement));
      });
      return value;
    },
  }),
}));

describe("OnboardingModal", () => {
  it("moves between steps and triggers the final action", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const onOpenFiles = vi.fn();
    render(
      <OnboardingModal
        onClose={onClose}
        onOpenFiles={onOpenFiles}
      />
    );

    expect(screen.getByText("ابدأ محادثتك")).toBeInTheDocument();
    await user.click(screen.getByText("التالي"));
    expect(screen.getByText("نظّم محادثاتك")).toBeInTheDocument();
    await user.click(screen.getByText("التالي"));
    expect(screen.getByText("استخدم ملفاتك")).toBeInTheDocument();
    await user.click(screen.getByText("افتح الملفات"));

    expect(onOpenFiles).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("can be skipped immediately", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<OnboardingModal onClose={onClose} />);

    await user.click(screen.getByText("تخطي"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
