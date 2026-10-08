import { renderHook, act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useConversationTitle from "./useConversationTitle";

vi.mock("../lib/conversationsApi", () => ({
  generateConversationTitle: vi.fn(),
}));

import { generateConversationTitle } from "../lib/conversationsApi";

describe("useConversationTitle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const baseProps = () => ({
    autoGenerateTitles: true,
    conversationId: 42,
    conversationSearch: "hello",
    loading: false,
    readOnlyConversation: false,
    refreshConversations: vi.fn(() => Promise.resolve()),
    selectedFolderId: 3,
    selectedProjectId: 4,
    selectedTagId: 5,
    selectedWorkspaceId: 6,
    setError: vi.fn(),
    setToast: vi.fn(),
    showArchivedConversations: false,
    showTrashConversations: false,
    t: (key) => key,
  });

  it("generates a title, clears the current error, and refreshes the conversation list", async () => {
    generateConversationTitle.mockResolvedValue({ title: "New title" });
    const props = baseProps();
    const { result } = renderHook(() => useConversationTitle(props));

    let response;
    await act(async () => {
      response = await result.current.handleGenerateConversationTitle();
    });

    expect(response).toEqual({ title: "New title" });
    expect(generateConversationTitle).toHaveBeenCalledWith(42);
    expect(props.setError).toHaveBeenCalledWith("");
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false,
      3,
      6,
      4,
      "hello",
      false,
      5
    );
    expect(props.setToast).toHaveBeenCalledWith({
      message: "conversationTitle.generated",
      type: "success",
    });
    expect(result.current.titleLoading).toBe(false);
  });

  it("skips manual generation for a read-only conversation", async () => {
    const props = { ...baseProps(), readOnlyConversation: true };
    const { result } = renderHook(() => useConversationTitle(props));

    await act(async () => {
      await result.current.handleGenerateConversationTitle();
    });

    expect(generateConversationTitle).not.toHaveBeenCalled();
    expect(props.setError).not.toHaveBeenCalled();
  });

  it("supports automatic title generation when enabled", async () => {
    generateConversationTitle.mockResolvedValue({ title: "Auto title" });
    const props = baseProps();
    const { result } = renderHook(() => useConversationTitle(props));

    await act(async () => {
      await result.current.maybeAutoGenerateConversationTitle(99);
    });

    expect(generateConversationTitle).toHaveBeenCalledWith(99);
    expect(props.setToast).toHaveBeenCalledWith({
      message: "Auto title",
      type: "success",
    });
  });
});
