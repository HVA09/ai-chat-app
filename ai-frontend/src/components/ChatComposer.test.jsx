import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { useState } from "react";
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
      "app.voiceInputNotSupported": "الإدخال الصوتي غير مدعوم في هذا المتصفح",
      "app.voiceInputError": "تعذر استخدام الإدخال الصوتي",
      "tools.modelSelector": "نموذج الذكاء الاصطناعي",
      "tools.attachFiles": "إرفاق ملفات",
      "tools.removeAttachment": "إزالة الملف",
      "tools.uploadingAttachment": "جارٍ رفع الملف...",
      "tools.dropFilesHere": "أسقط الملفات هنا",
    })[key] ?? key,
  }),
}));

describe("ChatComposer tools", () => {
  it("provides an explicit accessible name for the message input", () => {
    render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
      />
    );

    const textarea = screen.getByPlaceholderText("اكتب رسالتك هنا...");
    expect(textarea).toHaveAttribute("aria-label", "اكتب رسالتك هنا...");
    expect(screen.getByRole("textbox", { name: "اكتب رسالتك هنا..." })).toBe(textarea);
  });

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

    await user.click(screen.getByTitle(/فتح أدوات الرسالة|tools\.mobileMenu/));
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

    await user.click(screen.getByTitle(/فتح أدوات الرسالة|tools\.mobileMenu/));
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

    await user.click(screen.getByTitle(/فتح أدوات الرسالة|tools\.mobileMenu/));
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

    await user.click(screen.getByTitle(/فتح أدوات الرسالة|tools\.mobileMenu/));
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

  it("يركّز مربع الكتابة بعد اختيار أداة", async () => {
    const user = userEvent.setup();
    const onInsertWebSearch = vi.fn();
    render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onInsertWebSearch={onInsertWebSearch}
      />
    );

    await user.click(screen.getByTitle(/فتح أدوات الرسالة|tools\.mobileMenu/));
    await user.click(screen.getByTitle("بحث الويب"));
    await waitFor(() => expect(screen.getByPlaceholderText("اكتب رسالتك هنا...")).toHaveFocus());
    expect(onInsertWebSearch).toHaveBeenCalledTimes(1);
  });

  it("يُظهر زر الميكروفون ويوضح عدم دعم المتصفح", async () => {
    Object.defineProperty(window, "SpeechRecognition", { configurable: true, writable: true, value: undefined });
    Object.defineProperty(window, "webkitSpeechRecognition", { configurable: true, writable: true, value: undefined });
    const user = userEvent.setup();
    const onVoiceError = vi.fn();

    render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onVoiceError={onVoiceError}
      />
    );

    const microphone = screen.getByTitle("الإدخال الصوتي غير مدعوم في هذا المتصفح");
    expect(microphone).toBeInTheDocument();
    await user.click(microphone);
    expect(onVoiceError).toHaveBeenCalledWith("الإدخال الصوتي غير مدعوم في هذا المتصفح");
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

    await user.click(screen.getByTitle(/فتح أدوات الرسالة|tools\.mobileMenu/));
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

    await user.click(screen.getByTitle(/فتح أدوات الرسالة|tools\.mobileMenu/));
    await user.click(screen.getByTitle("وضع الوكيل"));
    expect(onInsertAgent).toHaveBeenCalled();
  });

});


describe("ChatComposer attachments", () => {
  it("يستدعي رفع الملفات عند اختيارها", async () => {
    const user = userEvent.setup();
    const onAttachFiles = vi.fn();
    const file = new File(["hello"], "notes.txt", { type: "text/plain" });

    render(
      <ChatComposer
        value="سؤال"
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onAttachFiles={onAttachFiles}
        attachments={[]}
      />
    );

    const input = screen.getByLabelText("إرفاق ملفات");
    await user.upload(input, file);

    expect(onAttachFiles).toHaveBeenCalledWith([file]);
  });

  it("keeps the attachment picker keyboard-accessible", async () => {
    const user = userEvent.setup();

    render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onAttachFiles={vi.fn()}
        attachments={[]}
      />
    );

    const textarea = screen.getByPlaceholderText("اكتب رسالتك هنا...");
    const input = screen.getByLabelText("إرفاق ملفات");
    textarea.focus();
    await user.tab();

    expect(input).toHaveFocus();
  });

  it("يتيح إعادة اختيار الملف نفسه بعد الاختيار الأول", async () => {
    const user = userEvent.setup();
    const onAttachFiles = vi.fn();
    const file = new File(["hello"], "retry.txt", { type: "text/plain" });

    render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onAttachFiles={onAttachFiles}
        attachments={[]}
      />
    );

    const input = screen.getByLabelText("إرفاق ملفات");
    await user.upload(input, file);
    expect(onAttachFiles).toHaveBeenCalledTimes(1);
    expect(onAttachFiles).toHaveBeenLastCalledWith([file]);

    // The file input must be cleared so the same file can be selected again after a failed upload.
    await user.upload(input, file);
    expect(onAttachFiles).toHaveBeenCalledTimes(2);
    expect(onAttachFiles).toHaveBeenLastCalledWith([file]);
  });

  it("يستطيع إزالة مرفق موجود", async () => {
    const user = userEvent.setup();
    const onRemoveAttachment = vi.fn();

    render(
      <ChatComposer
        value="سؤال"
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onRemoveAttachment={onRemoveAttachment}
        attachments={[{ id: 7, original_filename: "notes.txt" }]}
      />
    );

    await user.click(screen.getByLabelText("إزالة الملف"));
    expect(onRemoveAttachment).toHaveBeenCalledWith(7);
  });

  it("does not submit until attachment upload finishes", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={onSend}
        onStop={vi.fn()}
        attachments={[{ id: 7, original_filename: "notes.txt" }]}
        attachmentUploading
      />
    );

    const sendButton = screen.getByRole("button", { name: "إرسال" });
    expect(sendButton).toBeDisabled();
    await user.click(sendButton);
    expect(onSend).not.toHaveBeenCalled();
  });

  it("allows sending an attachment-only message after upload finishes", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={onSend}
        onStop={vi.fn()}
        attachments={[{ id: 7, original_filename: "notes.txt" }]}
        attachmentUploading={false}
      />
    );

    const sendButton = screen.getByRole("button", { name: "إرسال" });
    expect(sendButton).toBeEnabled();
    await user.click(sendButton);
    expect(onSend).toHaveBeenCalledTimes(1);
  });

});


describe("ChatComposer command autocomplete", () => {
  function StatefulComposer() {
    const [value, setValue] = useState("");
    return (
      <ChatComposer
        value={value}
        setValue={setValue}
        onSend={vi.fn()}
        onStop={vi.fn()}
      />
    );
  }

  it("shows matching slash commands and selects one with Enter", async () => {
    const user = userEvent.setup();

    render(<StatefulComposer />);

    const textarea = screen.getByPlaceholderText("اكتب رسالتك هنا...");
    await user.type(textarea, "/cal");
    expect(screen.getByRole("option", { name: /\/calc/ })).toBeInTheDocument();

    await user.keyboard("{Enter}");
    expect(textarea).toHaveValue("/calc ");
  });

  it("supports ArrowDown navigation before selecting a command", async () => {
    const user = userEvent.setup();

    render(<StatefulComposer />);

    const textarea = screen.getByPlaceholderText("اكتب رسالتك هنا...");
    await user.type(textarea, "/");
    await user.keyboard("{ArrowDown}");
    await user.keyboard("{Enter}");
    expect(textarea).toHaveValue("/search ");
  });
});


describe("ChatComposer responsive tools menu", () => {
  it("renders the tools menu in a dedicated responsive popover", async () => {
    const user = userEvent.setup();

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
        onInsertPython={vi.fn()}
        onCompareModels={vi.fn()}
        models={[
          { id: "model-a", label: "Model A" },
          { id: "model-b", label: "Model B" },
        ]}
      />
    );

    await user.click(screen.getByTitle("tools.mobileMenu"));
    const popover = screen.getByTitle("الآلة الحاسبة").closest(".chat-tools-popover");

    expect(popover).toBeInTheDocument();
    expect(popover).toHaveClass("ui-popover");
    expect(screen.getByTitle("بحث الويب")).toBeInTheDocument();
    expect(screen.getByTitle("تحليل البيانات")).toBeInTheDocument();
    expect(screen.getByTitle("وضع الوكيل")).toBeInTheDocument();
    expect(screen.getByTitle("مفسّر بايثون آمن")).toBeInTheDocument();
    expect(screen.getByTitle("tools.compareModels")).toBeInTheDocument();
    expect(popover).toHaveAttribute("role", "group");
    expect(popover).toHaveAttribute("aria-label", document.documentElement.lang === "ar" ? "أدوات الرسالة" : "Message tools");
  });

  it("closes the tools menu with Escape and restores focus to its trigger", async () => {
    const user = userEvent.setup();
    render(<ChatComposer value="" setValue={vi.fn()} onSend={vi.fn()} onStop={vi.fn()} />);

    const trigger = screen.getByTitle("tools.mobileMenu");
    await user.click(trigger);
    expect(screen.getByTitle("الآلة الحاسبة")).toBeInTheDocument();

    await user.keyboard("{Escape}");

    expect(screen.queryByTitle("الآلة الحاسبة")).not.toBeInTheDocument();
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(trigger).toHaveFocus();
  });

  it("closes the tools menu when the user clicks outside it", async () => {
    const user = userEvent.setup();
    render(<ChatComposer value="" setValue={vi.fn()} onSend={vi.fn()} onStop={vi.fn()} />);

    const trigger = screen.getByTitle("tools.mobileMenu");
    await user.click(trigger);
    expect(screen.getByTitle("الآلة الحاسبة")).toBeInTheDocument();

    await user.click(document.body);

    expect(screen.queryByTitle("الآلة الحاسبة")).not.toBeInTheDocument();
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });
});



describe("ChatComposer attachment intake guards", () => {
  const file = () => new File(["hello"], "notes.txt", { type: "text/plain" });

  it("forwards dropped files when the composer is ready", () => {
    const onAttachFiles = vi.fn();
    const { container } = render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onAttachFiles={onAttachFiles}
      />
    );

    fireEvent.drop(container.querySelector("form.chat-composer"), {
      dataTransfer: { files: [file()] },
    });

    expect(onAttachFiles).toHaveBeenCalledWith([
      expect.objectContaining({ name: "notes.txt" }),
    ]);
  });

  it.each([
    ["sending a message", { loading: true }],
    ["editing a message", { isEditing: true }],
    ["uploading another attachment", { attachmentUploading: true }],
  ])("ignores dropped files while %s", (_state, props) => {
    const onAttachFiles = vi.fn();
    const { container } = render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onAttachFiles={onAttachFiles}
        {...props}
      />
    );

    fireEvent.drop(container.querySelector("form.chat-composer"), {
      dataTransfer: { files: [file()] },
    });

    expect(onAttachFiles).not.toHaveBeenCalled();
  });

  it.each([
    ["sending a message", { loading: true }],
    ["editing a message", { isEditing: true }],
    ["uploading another attachment", { attachmentUploading: true }],
  ])("ignores pasted files while %s", (_state, props) => {
    const onAttachFiles = vi.fn();
    render(
      <ChatComposer
        value=""
        setValue={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
        onAttachFiles={onAttachFiles}
        {...props}
      />
    );

    fireEvent.paste(screen.getByRole("textbox", { name: "اكتب رسالتك هنا..." }), {
      clipboardData: { files: [file()] },
    });

    expect(onAttachFiles).not.toHaveBeenCalled();
  });
});


describe("ChatComposer voice recognition lifecycle", () => {
  it.each([
    ["sending a message", { loading: true }],
    ["editing a message", { isEditing: true }],
    ["uploading an attachment", { attachmentUploading: true }],
  ])("stops active voice recognition when %s begins", async (_state, busyProps) => {
    const originalDescriptor = Object.getOwnPropertyDescriptor(window, "SpeechRecognition");
    const instances = [];
    class MockRecognition {
      constructor() {
        this.stopCalls = 0;
        instances.push(this);
      }
      start() {
        this.onstart?.();
      }
      stop() {
        this.stopCalls += 1;
        this.onend?.();
      }
    }

    Object.defineProperty(window, "SpeechRecognition", {
      configurable: true,
      writable: true,
      value: MockRecognition,
    });

    try {
      const user = userEvent.setup();
      const setValue = vi.fn();
      const props = {
        value: "",
        setValue,
        onSend: vi.fn(),
        onStop: vi.fn(),
        onVoiceError: vi.fn(),
      };
      const { rerender } = render(<ChatComposer {...props} />);

      await user.click(screen.getByTitle("إدخال صوتي"));
      expect(instances).toHaveLength(1);
      expect(instances[0].stopCalls).toBe(0);

      rerender(<ChatComposer {...props} {...busyProps} />);
      expect(instances[0].stopCalls).toBe(1);

      // A late recognition event after stop must not mutate the next draft.
      instances[0].onresult?.({
        results: [[{ transcript: "نص متأخر" }]],
      });
      expect(setValue).not.toHaveBeenCalled();
    } finally {
      if (originalDescriptor) {
        Object.defineProperty(window, "SpeechRecognition", originalDescriptor);
      } else {
        delete window.SpeechRecognition;
      }
    }
  });

  it("prevents starting voice recognition during an attachment upload", async () => {
    const originalDescriptor = Object.getOwnPropertyDescriptor(window, "SpeechRecognition");
    const instances = [];
    class MockRecognition {
      constructor() {
        instances.push(this);
      }
      start() {}
      stop() {}
    }

    Object.defineProperty(window, "SpeechRecognition", {
      configurable: true,
      writable: true,
      value: MockRecognition,
    });

    try {
      const user = userEvent.setup();
      render(
        <ChatComposer
          value=""
          setValue={vi.fn()}
          onSend={vi.fn()}
          onStop={vi.fn()}
          attachmentUploading
        />
      );

      const voiceButton = screen.getByRole("button", { name: "إدخال صوتي" });
      expect(voiceButton).toBeDisabled();
      await user.click(voiceButton);
      expect(instances).toHaveLength(0);
    } finally {
      if (originalDescriptor) {
        Object.defineProperty(window, "SpeechRecognition", originalDescriptor);
      } else {
        delete window.SpeechRecognition;
      }
    }
  });
});
