import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useStartNewChat from "./useStartNewChat";

describe("useStartNewChat", () => {
  it("resets the active chat state to a fresh welcome chat", () => {
    const calls = [];
    const props = {
      t: "ar",
      messageCountRef: { current: 9 },
      resetChatAttachments: vi.fn(() => calls.push("resetChatAttachments")),
      setToolActivity: vi.fn((value) => calls.push(["tool", value])),
      setShowShareManager: vi.fn((value) => calls.push(["shareManager", value])),
      setWorkspaceShare: vi.fn((value) => calls.push(["workspaceShare", value])),
      setReadOnlyConversation: vi.fn((value) => calls.push(["readonly", value])),
      setShowWorkspaceComments: vi.fn((value) => calls.push(["comments", value])),
      setSelectedConversationIds: vi.fn((value) => calls.push(["selected", value])),
      setConversationId: vi.fn((value) => calls.push(["conversationId", value])),
      setConversationBranches: vi.fn((value) => calls.push(["branches", value])),
      setParentConversationId: vi.fn((value) => calls.push(["parent", value])),
      setMessages: vi.fn((value) => calls.push(["messages", value])),
      setInput: vi.fn((value) => calls.push(["input", value])),
      setEditingMessageIndex: vi.fn((value) => calls.push(["editing", value])),
      setError: vi.fn((value) => calls.push(["error", value])),
      getWelcomeMessage: vi.fn(() => ({ role: "assistant", text: "Welcome" })),
    };

    const { result } = renderHook(() => useStartNewChat(props));

    result.current.startNewChat();

    expect(props.messageCountRef.current).toBe(1);
    expect(props.getWelcomeMessage).toHaveBeenCalledWith("ar");
    expect(props.setConversationId).toHaveBeenCalledWith(null);
    expect(props.setConversationBranches).toHaveBeenCalledWith([]);
    expect(props.setParentConversationId).toHaveBeenCalledWith(null);
    expect(props.setMessages).toHaveBeenCalledWith([
      { role: "assistant", text: "Welcome" },
    ]);
    expect(props.resetChatAttachments).toHaveBeenCalled();
    expect(props.setInput).toHaveBeenCalledWith("");
    expect(props.setError).toHaveBeenCalledWith("");
  });
});
