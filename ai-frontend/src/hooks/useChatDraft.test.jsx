import { act, renderHook, waitFor } from "@testing-library/react";
import useChatDraft from "./useChatDraft";

describe("useChatDraft", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("hydrates the draft for the active user and conversation", async () => {
    window.localStorage.setItem("ai-chat-draft:7:12", "saved draft");

    const { result } = renderHook(() =>
      useChatDraft({ authed: true, userId: 7, conversationId: 12 })
    );

    await waitFor(() => {
      expect(result.current.input).toBe("saved draft");
    });
  });

  it("persists edited drafts and can reset the current input", async () => {
    const { result } = renderHook(() =>
      useChatDraft({ authed: true, userId: 7, conversationId: null })
    );

    await waitFor(() => {
      expect(result.current.input).toBe("");
    });

    act(() => {
      result.current.setInput("new draft");
    });

    await waitFor(() => {
      expect(window.localStorage.getItem("ai-chat-draft:7:new")).toBe("new draft");
    });

    act(() => {
      result.current.resetChatDraft();
    });

    expect(result.current.input).toBe("");
  });
});
