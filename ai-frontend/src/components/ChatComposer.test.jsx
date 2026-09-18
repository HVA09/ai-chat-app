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
    })[key] ?? key,
  }),
}));

describe("ChatComposer tools", () => {
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
});
