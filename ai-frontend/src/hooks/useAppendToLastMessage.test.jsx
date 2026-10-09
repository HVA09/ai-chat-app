import { useState } from "react";
import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import useAppendToLastMessage from "./useAppendToLastMessage";

describe("useAppendToLastMessage", () => {
  it("appends chunks to the last message while preserving its metadata", () => {
    const initialMessages = [
      { role: "user", text: "Question" },
      {
        role: "assistant",
        text: "Hel",
        feedback: "up",
        sources: [{ title: "Guide" }],
      },
    ];

    const { result } = renderHook(() => {
      const [messages, setMessages] = useState(initialMessages);
      const appendToLastMessage = useAppendToLastMessage({ setMessages });
      return { messages, appendToLastMessage };
    });

    act(() => {
      result.current.appendToLastMessage("lo");
      result.current.appendToLastMessage("!");
    });

    expect(result.current.messages).toEqual([
      { role: "user", text: "Question" },
      {
        role: "assistant",
        text: "Hello!",
        feedback: "up",
        sources: [{ title: "Guide" }],
      },
    ]);
    expect(initialMessages[1].text).toBe("Hel");
  });

  it("updates only the last message when several messages exist", () => {
    const initialMessages = [
      { role: "user", text: "A" },
      { role: "assistant", text: "B" },
      { role: "user", text: "C" },
      { role: "assistant", text: "" },
    ];

    const { result } = renderHook(() => {
      const [messages, setMessages] = useState(initialMessages);
      const appendToLastMessage = useAppendToLastMessage({ setMessages });
      return { messages, appendToLastMessage };
    });

    act(() => {
      result.current.appendToLastMessage("reply");
    });

    expect(result.current.messages.map((message) => message.text)).toEqual([
      "A",
      "B",
      "C",
      "reply",
    ]);
  });
});
