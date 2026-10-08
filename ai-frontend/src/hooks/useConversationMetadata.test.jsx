import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useConversationMetadata from "./useConversationMetadata";
import {
  generateConversationTitle,
  summarizeConversation,
} from "../lib/conversationsApi";

vi.mock("../lib/conversationsApi", () => ({
  generateConversationTitle: vi.fn(),
  summarizeConversation: vi.fn(),
}));

function createProps(overrides = {}) {
  return {
    conversationId: 7,
    loading: false,
    titleLoading: false,
    summaryLoading: false,
    readOnlyConversation: false,
    autoGenerateTitles: true,
    autoGenerateSummaries: true,
    conversationSearch: "",
    showArchivedConversations: false,
    showTrashConversations: false,
    selectedFolderId: null,
    selectedWorkspaceId: 2,
    selectedProjectId: 3,
    selectedTagId: null,
    messageCountRef: { current: 12 },
    autoSummaryLastMessageCountRef: { current: {} },
    autoSummaryInFlightRef: { current: false },
    refreshConversations: vi.fn(),
    setConversationSummary: vi.fn(),
    setConversationSummaryUpdatedAt: vi.fn(),
    setSummaryLoading: vi.fn(),
    setTitleLoading: vi.fn(),
    setError: vi.fn(),
    setToast: vi.fn(),
    t: (key) => key,
    ...overrides,
  };
}

describe("useConversationMetadata", () => {
  it("generates a title and refreshes the conversation list", async () => {
    generateConversationTitle.mockResolvedValue({ title: "New title" });
    const props = createProps();
    const { result } = renderHook(() => useConversationMetadata(props));

    await act(async () => {
      await result.current.handleGenerateConversationTitle();
    });

    expect(generateConversationTitle).toHaveBeenCalledWith(7);
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false,
      null,
      2,
      3,
      "",
      false,
      null
    );
    expect(props.setToast).toHaveBeenCalledWith({
      message: "conversationTitle.generated",
      type: "success",
    });
    expect(props.setTitleLoading).toHaveBeenLastCalledWith(false);
  });

  it("auto-summarizes only after the threshold and records the last count", async () => {
    summarizeConversation.mockResolvedValue({
      summary: "Summary",
      summary_updated_at: "2026-10-08T10:00:00Z",
    });
    const props = createProps();
    const { result } = renderHook(() => useConversationMetadata(props));

    await act(async () => {
      await result.current.maybeAutoSummarizeConversation(7, 11);
    });
    expect(summarizeConversation).not.toHaveBeenCalled();

    await act(async () => {
      await result.current.maybeAutoSummarizeConversation(7, 12);
    });

    expect(summarizeConversation).toHaveBeenCalledWith(7);
    expect(props.autoSummaryLastMessageCountRef.current[7]).toBe(12);
    expect(props.setConversationSummary).toHaveBeenCalledWith("Summary");
    expect(props.setConversationSummaryUpdatedAt).toHaveBeenCalledWith(
      "2026-10-08T10:00:00Z"
    );
  });

  it("does not overwrite the visible summary for a different conversation", async () => {
    summarizeConversation.mockResolvedValue({
      summary: "Other summary",
      summary_updated_at: "2026-10-08T10:00:00Z",
    });
    const props = createProps({ conversationId: 9 });
    const { result } = renderHook(() => useConversationMetadata(props));

    await act(async () => {
      await result.current.maybeAutoSummarizeConversation(7, 12);
    });

    expect(props.setConversationSummary).not.toHaveBeenCalled();
    expect(props.setConversationSummaryUpdatedAt).not.toHaveBeenCalled();
  });
});
