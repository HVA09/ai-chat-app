import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useConversationSharing from "./useConversationSharing";

const createConversationShareMock = vi.fn();

vi.mock("../lib/sharedConversationsApi", () => ({
  createConversationShare: (...args) => createConversationShareMock(...args),
}));

describe("useConversationSharing", () => {
  it("opens the share manager only when a conversation can be managed", () => {
    const setShowShareManager = vi.fn();
    const { result } = renderHook(() =>
      useConversationSharing({
        conversationId: 12,
        loading: false,
        messages: [],
        setShowShareManager,
        setToast: vi.fn(),
        t: (key) => key,
      })
    );

    result.current.handleManageConversationShares();

    expect(setShowShareManager).toHaveBeenCalledWith(true);
  });

  it("rejects protected-share passwords shorter than eight characters", async () => {
    const setToast = vi.fn();
    const originalConfirm = window.confirm;
    const originalPrompt = window.prompt;
    window.confirm = vi.fn(() => true);
    window.prompt = vi.fn(() => "short");

    try {
      const { result } = renderHook(() =>
        useConversationSharing({
          conversationId: 12,
          loading: false,
          messages: [],
          setShowShareManager: vi.fn(),
          setToast,
          t: (key) => key,
        })
      );

      await result.current.handleShareConversation();

      expect(createConversationShareMock).not.toHaveBeenCalled();
      expect(setToast).toHaveBeenCalledWith({
        message: "sharing.passwordTooShort",
        type: "error",
      });
    } finally {
      window.confirm = originalConfirm;
      window.prompt = originalPrompt;
    }
  });
});
