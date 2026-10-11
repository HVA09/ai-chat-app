import { describe, expect, it } from "vitest";
import i18n from "./i18n";

describe("i18n language namespaces", () => {
  it("keeps public assistant labels in the correct language", () => {
    expect(i18n.getResource("ar", "translation", "publicAssistant.backToApp")).toBe("الرجوع للتطبيق");
    expect(i18n.getResource("en", "translation", "publicAssistant.backToApp")).toBe("Back to app");
  });

  it("keeps command palette labels in the correct language", () => {
    expect(i18n.getResource("ar", "translation", "commandPalette.title")).toBe("لوحة الأوامر");
    expect(i18n.getResource("en", "translation", "commandPalette.title")).toBe("Command palette");
  });

  it("keeps project editor labels in the correct language", () => {
    expect(i18n.getResource("ar", "translation", "projectEditor.createTitle")).toBe("إنشاء مشروع");
    expect(i18n.getResource("en", "translation", "projectEditor.createTitle")).toBe("Create project");
  });

  it("keeps assistant editor labels in the correct language", () => {
    expect(i18n.getResource("ar", "translation", "assistantEditor.createTitle")).toBe("إنشاء مساعد");
    expect(i18n.getResource("en", "translation", "assistantEditor.createTitle")).toBe("Create assistant");
    expect(i18n.getResource("en", "translation", "assistantEditor.publicTitle")).toBe("Public link");
  });
});
