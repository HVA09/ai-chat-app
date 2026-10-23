import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import useChatAutoScroll from "./useChatAutoScroll";

function Harness({ conversationId, messages, loading = false }) {
  const { scrollContainerRef, handleScroll } = useChatAutoScroll({
    conversationId,
    messages,
    loading,
  });

  return (
    <div
      data-testid="chat-scroll"
      ref={(node) => {
        scrollContainerRef.current = node;
        if (!node) return;
        Object.defineProperty(node, "scrollHeight", {
          configurable: true,
          value: 1000,
        });
        Object.defineProperty(node, "clientHeight", {
          configurable: true,
          value: 300,
        });
      }}
      onScroll={handleScroll}
    >
      {messages.map((message, index) => (
        <p key={index}>{message.text}</p>
      ))}
    </div>
  );
}

describe("useChatAutoScroll", () => {
  it("starts a conversation at the latest message", () => {
    render(
      <Harness
        conversationId={8}
        messages={[
          { role: "user", text: "older" },
          { role: "assistant", text: "latest" },
        ]}
      />
    );

    expect(screen.getByTestId("chat-scroll").scrollTop).toBe(1000);
  });

  it("does not pull the reader back down while an older message is being read", () => {
    const messages = [
      { role: "user", text: "question" },
      { role: "assistant", text: "first chunk" },
    ];
    const { rerender } = render(
      <Harness conversationId={8} messages={messages} loading />
    );
    const scroller = screen.getByTestId("chat-scroll");

    scroller.scrollTop = 100;
    fireEvent.scroll(scroller);
    rerender(
      <Harness
        conversationId={8}
        loading
        messages={[
          messages[0],
          { role: "assistant", text: "updated streamed chunk" },
        ]}
      />
    );

    expect(scroller.scrollTop).toBe(100);
  });

  it("follows new stream updates when the reader is near the bottom", () => {
    const { rerender } = render(
      <Harness
        conversationId={8}
        loading
        messages={[{ role: "assistant", text: "first chunk" }]}
      />
    );
    const scroller = screen.getByTestId("chat-scroll");
    scroller.scrollTop = 680;
    fireEvent.scroll(scroller);

    rerender(
      <Harness
        conversationId={8}
        loading
        messages={[{ role: "assistant", text: "second chunk" }]}
      />
    );

    expect(scroller.scrollTop).toBe(1000);
  });

  it("returns to the bottom when a new user message is submitted", () => {
    const messages = [{ role: "assistant", text: "previous answer" }];
    const { rerender } = render(
      <Harness conversationId={8} messages={messages} />
    );
    const scroller = screen.getByTestId("chat-scroll");
    scroller.scrollTop = 100;
    fireEvent.scroll(scroller);

    rerender(
      <Harness
        conversationId={8}
        messages={[
          ...messages,
          { role: "user", text: "new question" },
        ]}
      />
    );

    expect(scroller.scrollTop).toBe(1000);
  });

  it("resets to the bottom after switching conversations", () => {
    const { rerender } = render(
      <Harness
        conversationId={8}
        messages={[{ role: "assistant", text: "answer one" }]}
      />
    );
    const scroller = screen.getByTestId("chat-scroll");
    scroller.scrollTop = 100;
    fireEvent.scroll(scroller);

    rerender(
      <Harness
        conversationId={9}
        messages={[{ role: "assistant", text: "answer two" }]}
      />
    );

    expect(scroller.scrollTop).toBe(1000);
  });
});
