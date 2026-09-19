import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import ChatMessage from "./ChatMessage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) =>
      ({
        you: "You",
        assistant: "Assistant",
        "feedback.helpful": "Helpful",
        "feedback.notHelpful": "Not helpful",
        "feedback.saved": "Feedback saved",
        "sources.title": "Sources",
      })[key] ?? key,
  }),
}));

describe("ChatMessage feedback", () => {
  it("shows feedback controls for assistant messages and submits thumbs up", async () => {
    const user = userEvent.setup();
    const onFeedback = vi.fn();

    render(
      <ChatMessage
        role="assistant"
        text="رد تجريبي"
        time="10:00"
        canFeedback
        onFeedback={onFeedback}
      />
    );

    expect(screen.getByRole("button", { name: "Helpful" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Not helpful" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Helpful" }));
    expect(onFeedback).toHaveBeenCalledWith(1);
  });

  it("submits thumbs down and displays the saved state", async () => {
    const user = userEvent.setup();
    const onFeedback = vi.fn();

    render(
      <ChatMessage
        role="assistant"
        text="رد تجريبي"
        time="10:00"
        feedback={-1}
        canFeedback
        onFeedback={onFeedback}
      />
    );

    expect(screen.getByText("Feedback saved")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Not helpful" }));
    expect(onFeedback).toHaveBeenCalledWith(-1);
  });

  it("does not show feedback controls for user messages", () => {
    render(
      <ChatMessage
        role="user"
        text="سؤال المستخدم"
        time="10:00"
        canFeedback
        onFeedback={vi.fn()}
      />
    );

    expect(screen.queryByRole("button", { name: "Helpful" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Not helpful" })).not.toBeInTheDocument();
  });
});
