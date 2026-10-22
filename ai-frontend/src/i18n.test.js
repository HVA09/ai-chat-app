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

  it("keeps speech input and output error messages distinct", () => {
    expect(i18n.getResource("ar", "translation", "app.voiceInputNotSupported")).toBe("الإدخال الصوتي غير مدعوم في هذا المتصفح");
    expect(i18n.getResource("ar", "translation", "app.voiceOutputNotSupported")).toBe("الإخراج الصوتي غير مدعوم في هذا المتصفح");
    expect(i18n.getResource("en", "translation", "app.voiceInputNotSupported")).toBe("Voice input is not supported in this browser");
    expect(i18n.getResource("en", "translation", "app.voiceOutputNotSupported")).toBe("Voice output is not supported in this browser");
  });

  it("keeps model selector labels translated in Arabic and English", () => {
    expect(i18n.getResource("ar", "translation", "tools.modelSelector")).toBe("نموذج الذكاء الاصطناعي");
    expect(i18n.getResource("en", "translation", "tools.modelSelector")).toBe("AI model");
    expect(i18n.getResource("ar", "translation", "tools.defaultModel")).toBe("النموذج الافتراضي");
    expect(i18n.getResource("en", "translation", "tools.defaultModel")).toBe("Default model");
  });

  it("keeps assistant editor labels in the correct language", () => {
    expect(i18n.getResource("ar", "translation", "assistantEditor.createTitle")).toBe("إنشاء مساعد");
    expect(i18n.getResource("en", "translation", "assistantEditor.createTitle")).toBe("Create assistant");
    expect(i18n.getResource("en", "translation", "assistantEditor.publicTitle")).toBe("Public link");
  });
  it("keeps mobile sidebar close labels translated in Arabic and English", () => {
    expect(i18n.getResource("ar", "translation", "sidebar.closeNavigation")).toBe("إغلاق القائمة الجانبية");
    expect(i18n.getResource("en", "translation", "sidebar.closeNavigation")).toBe("Close sidebar");
  });

});
