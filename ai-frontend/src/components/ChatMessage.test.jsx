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
        "sources.chunkShort": "chunk {{chunk}}",
        "sources.preview": "Preview source",
        "sources.hidePreview": "Hide source preview",
        "bookmarks.save": "Save message",
        "bookmarks.remove": "Remove from bookmarks",
        "memory.save": "Save to memory",
        "memory.remove": "Remove from memory",
        "chat.branchConversation": "Branch conversation",
        "tools.voiceOutput": "Read aloud",
        "tools.stopVoiceOutput": "Stop reading",
        "app.voiceNotSupported": "Voice output is not supported in this browser",
        "app.voiceError": "Couldn't read the message aloud",
      })[key] ?? key,
  }),
}));

describe("ChatMessage voice output", () => {
  it("speaks assistant text when read aloud is pressed", async () => {
    const user = userEvent.setup();
    const speak = vi.fn((utterance) => utterance.onstart?.());

    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: { speak, cancel: vi.fn() },
    });
    window.SpeechSynthesisUtterance = class {
      constructor(text) {
        this.text = text;
        this.lang = "";
        this.rate = 0;
        this.pitch = 0;
      }
    };

    document.documentElement.lang = "en";
    render(<ChatMessage role="assistant" text="Hello from AI" time="10:00" />);

    await user.click(screen.getByRole("button", { name: "Read aloud" }));

    expect(speak).toHaveBeenCalledTimes(1);
    expect(speak.mock.calls[0][0].text).toBe("Hello from AI");
    expect(speak.mock.calls[0][0].lang).toBe("en-US");
    expect(screen.getByRole("button", { name: "Stop reading" })).toBeInTheDocument();
  });
});

describe("ChatMessage source preview", () => {
  it("expands and collapses a source snippet on demand", async () => {
    const user = userEvent.setup();

    render(
      <ChatMessage
        role="assistant"
        text="Uses [S1]."
        time="10:00"
        sources={[
          {
            id: "S1",
            filename: "linux.pdf",
            chunk: 2,
            snippet: "A useful Linux command line excerpt.",
            file_id: 42,
          },
        ]}
      />
    );

    expect(screen.queryByText("A useful Linux command line excerpt.")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Preview source" }));
    expect(screen.getByText("A useful Linux command line excerpt.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Hide source preview" }));
    expect(screen.queryByText("A useful Linux command line excerpt.")).not.toBeInTheDocument();
  });
});

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
  it("renders cited source ids as inline links", () => {
    render(
      <ChatMessage
        role="assistant"
        text="The answer uses [S1]."
        time="10:00"
        sources={[{ id: "S1", filename: "linux.pdf", chunk: 2, file_id: 42 }]}
      />
    );

    const citation = screen.getByRole("link", { name: "[S1]" });
    expect(citation).toHaveAttribute("href", expect.stringMatching(/^#/));
  });

  it("does not turn unknown source ids into links", () => {
    render(
      <ChatMessage
        role="assistant"
        text="The answer mentions [S2] but only S1 exists."
        time="10:00"
        sources={[{ id: "S1", filename: "linux.pdf", chunk: 2, file_id: 42 }]}
      />
    );

    expect(screen.queryByRole("link", { name: "[S2]" })).not.toBeInTheDocument();
    expect(screen.getByText(/\[S2\]/)).toBeInTheDocument();
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

describe("ChatMessage memory", () => {
  it("shows and calls the save-memory control for user messages", async () => {
    const user = userEvent.setup();
    const onToggleRemember = vi.fn();

    render(
      <ChatMessage
        role="user"
        text="I prefer concise answers"
        time="10:00"
        canRemember
        onToggleRemember={onToggleRemember}
      />
    );

    expect(screen.getByRole("button", { name: "Save to memory" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save to memory" }));
    expect(onToggleRemember).toHaveBeenCalled();
  });

  it("shows remove-from-memory when the message is remembered", () => {
    render(
      <ChatMessage
        role="user"
        text="I prefer concise answers"
        time="10:00"
        canRemember
        isRemembered
        onToggleRemember={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: "Remove from memory" })).toBeInTheDocument();
  });

  it("does not show memory controls for assistant messages", () => {
    render(
      <ChatMessage
        role="assistant"
        text="Assistant reply"
        time="10:00"
        canRemember
        onToggleRemember={vi.fn()}
      />
    );

    expect(screen.queryByRole("button", { name: "Save to memory" })).not.toBeInTheDocument();
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
