import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useMessageFeedback from "./useMessageFeedback";

describe("useMessageFeedback", () => {
  function createProps(overrides = {}) {
    return {
      conversationId: 12,
      loading: false,
      readOnlyConversation: false,
      messages: [
        { role: "user", text: "Hello" },
        { role: "assistant", text: "Hi", feedback: null },
      ],
      setMessages: vi.fn(),
      setMessageFeedback: vi.fn(),
      setToast: vi.fn(),
      t: vi.fn((key) => key),
      ...overrides,
    };
  }

  it("optimistically toggles feedback and persists it", async () => {
    const props = createProps();
    const { result } = renderHook(() => useMessageFeedback(props));

    await act(async () => {
      await result.current.handleMessageFeedback(1, "up");
    });

    expect(props.setMessages).toHaveBeenCalledWith(expect.any(Function));
    expect(props.setMessageFeedback).toHaveBeenCalledWith(12, 2, "up");
  });

  it("rolls back and shows an error when persistence fails", async () => {
    const props = createProps({
      setMessageFeedback: vi.fn().mockRejectedValue(new Error("failed")),
    });
    const { result } = renderHook(() => useMessageFeedback(props));

    await act(async () => {
      await result.current.handleMessageFeedback(1, "down");
    });

    expect(props.setMessages).toHaveBeenCalledTimes(2);
    expect(props.setToast).toHaveBeenCalledWith({
      message: "app.feedbackError",
      type: "error",
    });
  });

  it("ignores feedback when the conversation is unavailable or read-only", async () => {
    const props = createProps({
      conversationId: null,
      readOnlyConversation: true,
    });
    const { result } = renderHook(() => useMessageFeedback(props));

    await act(async () => {
      await result.current.handleMessageFeedback(1, "up");
    });

    expect(props.setMessages).not.toHaveBeenCalled();
    expect(props.setMessageFeedback).not.toHaveBeenCalled();
  });
});
