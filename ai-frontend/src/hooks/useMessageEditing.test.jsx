import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useMessageEditing from "./useMessageEditing";

const buildProps = (overrides = {}) => ({
  readOnlyConversation: false,
  loading: false,
  conversationId: "conversation-1",
  messages: [{ role: "user", text: "Hello" }],
  resetChatAttachments: vi.fn(),
  setError: vi.fn(),
  setRetryableUserMessage: vi.fn(),
  setEditingMessageIndex: vi.fn(),
  setInput: vi.fn(),
  ...overrides,
});

describe("useMessageEditing", () => {
  it("starts editing an editable user message", () => {
    const props = buildProps();
    const { result } = renderHook(() => useMessageEditing(props));

    act(() => result.current.startEditingMessage(0));

    expect(props.setError).toHaveBeenCalledWith("");
    expect(props.setRetryableUserMessage).toHaveBeenCalledWith(null);
    expect(props.resetChatAttachments).toHaveBeenCalled();
    expect(props.setEditingMessageIndex).toHaveBeenCalledWith(0);
    expect(props.setInput).toHaveBeenCalledWith("Hello");
  });

  it("ignores editing when the conversation is not editable", () => {
    const props = buildProps({ readOnlyConversation: true });
    const { result } = renderHook(() => useMessageEditing(props));

    act(() => result.current.startEditingMessage(0));

    expect(props.setEditingMessageIndex).not.toHaveBeenCalled();
    expect(props.setInput).not.toHaveBeenCalled();
  });

  it("cancels editing and clears the draft state", () => {
    const props = buildProps();
    const { result } = renderHook(() => useMessageEditing(props));

    act(() => result.current.cancelEditing());

    expect(props.setEditingMessageIndex).toHaveBeenCalledWith(null);
    expect(props.setInput).toHaveBeenCalledWith("");
    expect(props.setError).toHaveBeenCalledWith("");
  });
});
