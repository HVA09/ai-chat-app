import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import ChatComposer from "./ChatComposer";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) => ({
      placeholder: "اكتب رسالتك هنا...",
      send: "إرسال",
      stop: "إيقاف",
      "tools.calculator": "الآلة الحاسبة",
      "tools.webSearch": "بحث الويب",
      "tools.dataAnalysis": "تحليل البيانات",
      "tools.agent": "وضع الوكيل",
      "tools.python": "مفسّر بايثون آمن",
      "tools.voiceInput": "إدخال صوتي",
      "tools.voiceStop": "إيقاف الإدخال الصوتي",
      "tools.modelSelector": "نموذج الذكاء الاصطناعي",
    })[key] ?? key,
  }),
}));

describe("ChatComposer tools", () => {
  it("زر بحث الويب يمرر المعالج", async () => {
    const user = userEvent.setup();
    const onInsertWebSearch = vi.fn();

    render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onInsertCalculator={vi.fn()}
        onInsertWebSearch={onInsertWebSearch}
      />
    );

    await user.click(screen.getByTitle("بحث الويب"));
    expect(onInsertWebSearch).toHaveBeenCalled();
  });

  it("زر تحليل البيانات يمرر المعالج", async () => {
    const user = userEvent.setup();
    const onInsertDataAnalysis = vi.fn();
    const onInsertPython = vi.fn();

    render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onInsertCalculator={vi.fn()}
        onInsertWebSearch={vi.fn()}
        onInsertDataAnalysis={onInsertDataAnalysis}
        onInsertPython={onInsertPython}
      />
    );

    await user.click(screen.getByTitle("تحليل البيانات"));
    expect(onInsertDataAnalysis).toHaveBeenCalled();
  });

  it("زر مفسّر بايثون يمرر المعالج", async () => {
    const user = userEvent.setup();
    const onInsertPython = vi.fn();

    render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onInsertCalculator={vi.fn()}
        onInsertWebSearch={vi.fn()}
        onInsertDataAnalysis={vi.fn()}
        onInsertAgent={vi.fn()}
        onInsertPython={onInsertPython}
      />
    );

    await user.click(screen.getByTitle("مفسّر بايثون آمن"));
    expect(onInsertPython).toHaveBeenCalled();
  });

  it("زر الآلة الحاسبة يمرر المعالج", async () => {
    const user = userEvent.setup();
    const onInsertCalculator = vi.fn();

    render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onInsertCalculator={onInsertCalculator}
      />
    );

    await user.click(screen.getByTitle("الآلة الحاسبة"));
    expect(onInsertCalculator).toHaveBeenCalled();
  });

  it("زر الإدخال الصوتي يضيف النص الناتج", async () => {
    class MockRecognition {
      start() {
        this.onstart?.();
        this.onresult?.({
          results: [[{ transcript: "اختبار صوتي" }]],
        });
        this.onend?.();
      }
      stop() {
        this.onend?.();
      }
    }

    Object.defineProperty(window, "SpeechRecognition", {
      configurable: true,
      writable: true,
      value: MockRecognition,
    });

    const user = userEvent.setup();
    let currentValue = "";
    const setValue = vi.fn((updater) => {
      currentValue =
        typeof updater === "function" ? updater(currentValue) : updater;
    });

    render(
      <ChatComposer
        value={currentValue}
        setValue={setValue}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onInsertCalculator={vi.fn()}
        onInsertWebSearch={vi.fn()}
        onInsertDataAnalysis={vi.fn()}
        onInsertAgent={vi.fn()}
      />
    );

    await user.click(screen.getByTitle("إدخال صوتي"));
    expect(currentValue).toBe("اختبار صوتي");
  });

  it("يتيح اختيار نموذج الذكاء الاصطناعي", async () => {
    const user = userEvent.setup();
    const onSelectModel = vi.fn();

    render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onInsertCalculator={vi.fn()}
        onInsertWebSearch={vi.fn()}
        onInsertDataAnalysis={vi.fn()}
        onInsertAgent={vi.fn()}
        models={[
          { id: "gemini-2.5-flash", label: "gemini-2.5-flash", is_default: true },
          { id: "gemini-test", label: "gemini-test", is_default: false },
        ]}
        selectedModel="gemini-2.5-flash"
        onSelectModel={onSelectModel}
      />
    );

    const select = screen.getByLabelText("نموذج الذكاء الاصطناعي");
    expect(screen.getByRole("option", { name: "gemini-2.5-flash" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "gemini-test" })).toBeInTheDocument();

    await user.selectOptions(select, "gemini-test");
    expect(onSelectModel).toHaveBeenCalledWith("gemini-test");
  });

  it("زر وضع الوكيل يمرر المعالج", async () => {
    const user = userEvent.setup();
    const onInsertAgent = vi.fn();

    render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onInsertCalculator={vi.fn()}
        onInsertWebSearch={vi.fn()}
        onInsertDataAnalysis={vi.fn()}
        onInsertAgent={onInsertAgent}
      />
    );

    await user.click(screen.getByTitle("وضع الوكيل"));
    expect(onInsertAgent).toHaveBeenCalled();
  });

});
