import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useMessageFeedback from "./useMessageFeedback";

vi.mock("../lib/chatApi", () => ({
  setMessageFeedback: vi.fn(),
}));

import { setMessageFeedback } from "../lib/chatApi";

const baseProps = () => ({
  conversationId: 12,
  loading: false,
  readOnlyConversation: false,
  messages: [
    { role: "user", text: "Hello", feedback: null },
    { role: "assistant", text: "Hi", feedback: "up" },
  ],
  setMessages: vi.fn((updater) => updater(baseProps().messages)),
  setToast: vi.fn(),
  t: (key) => key,
});

describe("useMessageFeedback", () => {
  it("optimistically sets a new rating", async () => {
    setMessageFeedback.mockResolvedValue(undefined);
    const setMessages = vi.fn();
    const props = { ...baseProps(), setMessages };

    const { result } = renderHook(() => useMessageFeedback(props));

    await act(async () => {
      await result.current.handleMessageFeedback(0, "up");
    });

    expect(setMessages).toHaveBeenCalled();
    expect(setMessageFeedback).toHaveBeenCalledWith(12, 1, "up");
  });

  it("toggles the same rating off", async () => {
    setMessageFeedback.mockResolvedValue(undefined);
    const setMessages = vi.fn();

    const { result } = renderHook(() =>
      useMessageFeedback({
        ...baseProps(),
        setMessages,
        messages: [{ feedback: "down" }],
      })
    );

    await act(async () => {
      await result.current.handleMessageFeedback(0, "down");
    });

    expect(setMessageFeedback).toHaveBeenCalledWith(12, 1, null);
  });

  it("rolls back optimistic state and shows an error on API failure", async () => {
    setMessageFeedback.mockRejectedValue(new Error("failed"));
    let currentMessages = [{ role: "assistant", text: "Hi", feedback: null }];
    const setMessages = vi.fn((updater) => {
      currentMessages = updater(currentMessages);
    });
    const setToast = vi.fn();

    const { result } = renderHook(() =>
      useMessageFeedback({
        ...baseProps(),
        messages: currentMessages,
        setMessages,
        setToast,
      })
    );

    await act(async () => {
      await result.current.handleMessageFeedback(0, "down");
    });

    expect(setMessages).toHaveBeenCalledTimes(2);
    expect(currentMessages[0].feedback).toBeNull();
    expect(setToast).toHaveBeenCalledWith({
      message: "app.feedbackError",
      type: "error",
    });
  });

  it("does nothing when feedback is not allowed", async () => {
    const setMessages = vi.fn();

    const { result } = renderHook(() =>
      useMessageFeedback({
        ...baseProps(),
        conversationId: null,
        setMessages,
      })
    );

    await act(async () => {
      await result.current.handleMessageFeedback(0, "up");
    });

    expect(setMessages).not.toHaveBeenCalled();
    expect(setMessageFeedback).not.toHaveBeenCalled();
  });
});
