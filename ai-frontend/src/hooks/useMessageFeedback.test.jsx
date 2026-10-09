import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useMessageFeedback from "./useMessageFeedback";

vi.mock("../lib/chatApi", () => ({
  setMessageFeedback: vi.fn(),
}));

import { setMessageFeedback } from "../lib/chatApi";

function createProps(overrides = {}) {
  return {
    conversationId: 12,
    loading: false,
    readOnlyConversation: false,
    messages: [
      { role: "user", text: "Hello", feedback: null },
      { role: "assistant", text: "Hi", feedback: "up" },
    ],
    setMessages: vi.fn(),
    setToast: vi.fn(),
    t: (key) => key,
    ...overrides,
  };
}

describe("useMessageFeedback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setMessageFeedback.mockReset();
  });

  it("optimistically applies a rating and persists it", async () => {
    setMessageFeedback.mockResolvedValue(undefined);
    const props = createProps();
    let currentMessages = props.messages;
    props.setMessages.mockImplementation((updater) => {
      currentMessages = updater(currentMessages);
    });

    const { result } = renderHook(() => useMessageFeedback(props));

    await act(async () => {
      await result.current.handleMessageFeedback(0, "up");
    });

    expect(currentMessages[0].feedback).toBe("up");
    expect(setMessageFeedback).toHaveBeenCalledWith(12, 1, "up");
  });

  it("turns the same rating off", async () => {
    setMessageFeedback.mockResolvedValue(undefined);
    const props = createProps({
      messages: [{ role: "assistant", text: "Hi", feedback: "down" }],
    });
    const { result } = renderHook(() => useMessageFeedback(props));

    await act(async () => {
      await result.current.handleMessageFeedback(0, "down");
    });

    expect(setMessageFeedback).toHaveBeenCalledWith(12, 1, null);
  });

  it("rolls back the rating and shows an error when persistence fails", async () => {
    setMessageFeedback.mockRejectedValue(new Error("failed"));
    const props = createProps({
      messages: [{ role: "assistant", text: "Hi", feedback: "up" }],
    });
    let currentMessages = props.messages;
    props.setMessages.mockImplementation((updater) => {
      currentMessages = updater(currentMessages);
    });

    const { result } = renderHook(() => useMessageFeedback(props));

    await act(async () => {
      await result.current.handleMessageFeedback(0, "down");
    });

    expect(currentMessages[0].feedback).toBe("up");
    expect(props.setMessages).toHaveBeenCalledTimes(2);
    expect(props.setToast).toHaveBeenCalledWith({
      message: "app.feedbackError",
      type: "error",
    });
  });

  it.each([
    ["missing conversation", { conversationId: null }],
    ["loading", { loading: true }],
    ["read-only conversation", { readOnlyConversation: true }],
  ])("does nothing when feedback is not allowed (%s)", async (_label, overrides) => {
    const props = createProps(overrides);
    const { result } = renderHook(() => useMessageFeedback(props));

    await act(async () => {
      await result.current.handleMessageFeedback(0, "up");
    });

    expect(props.setMessages).not.toHaveBeenCalled();
    expect(setMessageFeedback).not.toHaveBeenCalled();
  });
});
