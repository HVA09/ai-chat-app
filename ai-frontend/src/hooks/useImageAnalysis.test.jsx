import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useImageAnalysis from "./useImageAnalysis";

describe("useImageAnalysis", () => {
  function createProps(overrides = {}) {
    const messageCountRef = { current: 4 };
    return {
      analyzeImage: vi.fn().mockResolvedValue({
        conversation_id: 42,
        reply: "analysis result",
      }),
      conversationId: 7,
      loading: false,
      readOnlyConversation: false,
      messageCountRef,
      setError: vi.fn(),
      setShowFiles: vi.fn(),
      setMessages: vi.fn(),
      setConversationId: vi.fn(),
      setLoading: vi.fn(),
      refreshConversations: vi.fn().mockResolvedValue(undefined),
      showArchivedConversations: false,
      selectedFolderId: null,
      selectedWorkspaceId: 3,
      selectedProjectId: null,
      maybeAutoSummarizeConversation: vi.fn(),
      setToast: vi.fn(),
      t: vi.fn((key) => key),
      ...overrides,
    };
  }

  it("adds image request messages and applies the response", async () => {
    const props = createProps();
    const { result } = renderHook(() => useImageAnalysis(props));

    await act(async () => {
      await result.current.handleAnalyzeImage(
        { id: 9, original_filename: "image.png" },
        "describe this"
      );
    });

    expect(props.messageCountRef.current).toBe(6);
    expect(props.setError).toHaveBeenCalledWith("");
    expect(props.setShowFiles).toHaveBeenCalledWith(false);
    expect(props.setLoading).toHaveBeenNthCalledWith(1, true);
    expect(props.analyzeImage).toHaveBeenCalledWith(7, 9, "describe this");
    expect(props.setConversationId).toHaveBeenCalledWith(42);
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false,
      null,
      3,
      null
    );
    expect(props.maybeAutoSummarizeConversation).toHaveBeenCalledWith(7, 6);
    expect(props.setLoading).toHaveBeenLastCalledWith(false);
  });

  it("rolls back optimistic messages and message count on failure", async () => {
    const error = new Error("image failed");
    const props = createProps({
      analyzeImage: vi.fn().mockRejectedValue(error),
    });
    const { result } = renderHook(() => useImageAnalysis(props));

    await expect(
      act(async () => {
        await result.current.handleAnalyzeImage(
          { id: 9, original_filename: "image.png" },
          "describe this"
        );
      })
    ).rejects.toBe(error);

    expect(props.messageCountRef.current).toBe(4);
    expect(props.setMessages).toHaveBeenLastCalledWith(expect.any(Function));
    expect(props.setToast).toHaveBeenCalledWith({
      message: "app.imageAnalyzeError",
      type: "error",
    });
    expect(props.setLoading).toHaveBeenLastCalledWith(false);
  });
});
