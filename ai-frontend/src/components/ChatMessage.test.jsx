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
        "bookmarks.save": "Save message",
        "bookmarks.remove": "Remove from bookmarks",
        "chat.branchConversation": "Branch conversation",
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

  it("toggles bookmark state for assistant messages", async () => {
    const user = userEvent.setup();
    const onToggleBookmark = vi.fn();

    render(
      <ChatMessage
        role="assistant"
        text="رد مهم"
        time="10:00"
        onToggleBookmark={onToggleBookmark}
      />
    );

    expect(screen.getByRole("button", { name: "Save message" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save message" }));
    expect(onToggleBookmark).toHaveBeenCalled();
  });

  it("shows remove-bookmark label when bookmarked", () => {
    render(
      <ChatMessage
        role="assistant"
        text="رد مهم"
        time="10:00"
        isBookmarked
        onToggleBookmark={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: "Remove from bookmarks" })).toBeInTheDocument();
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
  it("renders file sources as clickable links", () => {
    render(
      <ChatMessage
        role="assistant"
        text="إجابة"
        time="10:00"
        sources={[{ id: "S1", filename: "linux.pdf", chunk: 2, file_id: 42 }]}
      />
    );

    const link = screen.getByRole("link", { name: /\[S1\] linux\.pdf/ });
    expect(link).toHaveAttribute("href", expect.stringContaining("/files/42"));
  });

});

describe("ChatMessage branching", () => {
  it("calls the branch handler for a message", async () => {
    const user = userEvent.setup();
    const onBranch = vi.fn();

    render(
      <ChatMessage
        role="assistant"
        text="رد"
        time="10:00"
        canBranch
        onBranch={onBranch}
      />
    );

    await user.click(screen.getByRole("button", { name: "Branch conversation" }));
    expect(onBranch).toHaveBeenCalled();
  });
});
