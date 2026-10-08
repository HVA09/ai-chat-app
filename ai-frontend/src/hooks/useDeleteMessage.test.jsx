import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import useDeleteMessage from "./useDeleteMessage";
import api from "../lib/api";
import { getConversation } from "../lib/conversationsApi";

vi.mock("../lib/api", () => ({
  default: { delete: vi.fn() },
}));

vi.mock("../lib/conversationsApi", () => ({
  getConversation: vi.fn(),
}));

describe("useDeleteMessage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.documentElement.lang = "en";
    window.confirm = vi.fn(() => true);
  });

  it("deletes the message, reloads the conversation, and refreshes the list", async () => {
    api.delete.mockResolvedValue({});
    getConversation.mockResolvedValue({
      messages: [
        {
          role: "user",
          content: "Hello",
          created_at: "2026-01-01T10:00:00Z",
          sources: [],
        },
      ],
    });

    const setError = vi.fn();
    const setMessages = vi.fn();
    const refreshConversations = vi.fn().mockResolvedValue(undefined);
    const getWelcomeMessage = vi.fn(() => ({ role: "assistant", text: "Welcome" }));
    const setToast = vi.fn();

    const { result } = renderHook(() =>
      useDeleteMessage({
        conversationId: 42,
        loading: false,
        editingMessageIndex: null,
        readOnlyConversation: false,
        setError,
        setMessages,
        refreshConversations,
        getWelcomeMessage,
        t: "translate",
        setToast,
      })
    );

    await act(async () => {
      await result.current.deleteMessage(2);
    });

    expect(window.confirm).toHaveBeenCalled();
    expect(api.delete).toHaveBeenCalledWith("/chat/42/messages/3");
    expect(setError).toHaveBeenCalledWith("");
    expect(setMessages).toHaveBeenCalledWith([
      expect.objectContaining({ role: "user", text: "Hello", sources: [] }),
    ]);
    expect(refreshConversations).toHaveBeenCalled();
    expect(setToast).not.toHaveBeenCalled();
  });

  it("stops without deleting when the conversation is read-only", async () => {
    const { result } = renderHook(() =>
      useDeleteMessage({
        conversationId: 42,
        loading: false,
        editingMessageIndex: null,
        readOnlyConversation: true,
        setError: vi.fn(),
        setMessages: vi.fn(),
        refreshConversations: vi.fn(),
        getWelcomeMessage: vi.fn(),
        t: vi.fn(),
        setToast: vi.fn(),
      })
    );

    await act(async () => {
      await result.current.deleteMessage(0);
    });

    expect(api.delete).not.toHaveBeenCalled();
    expect(window.confirm).not.toHaveBeenCalled();
  });
});
