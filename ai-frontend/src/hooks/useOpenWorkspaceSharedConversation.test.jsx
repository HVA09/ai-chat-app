import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useOpenWorkspaceSharedConversation from "./useOpenWorkspaceSharedConversation";

vi.mock("../lib/workspaceConversationSharesApi", () => ({
  getWorkspaceSharedConversation: vi.fn(),
}));

import { getWorkspaceSharedConversation } from "../lib/workspaceConversationSharesApi";

describe("useOpenWorkspaceSharedConversation", () => {
  it("loads a shared conversation into read-only mode", async () => {
    getWorkspaceSharedConversation.mockResolvedValue({
      conversation_id: 44,
      messages: [
        {
          role: "user",
          content: "Hello",
          created_at: "2026-10-07T18:00:00Z",
          sources: ["source"],
        },
      ],
    });

    const setters = Object.fromEntries(
      [
        "setShowShareManager",
        "setReadOnlyConversation",
        "setShowWorkspaceComments",
        "setWorkspaceShare",
        "setSelectedWorkspaceId",
        "setConversationId",
        "setConversationSummary",
        "setConversationSummaryUpdatedAt",
        "setSelectedAssistantId",
        "setSelectedFolderId",
        "setSelectedProjectId",
        "setSelectedModel",
        "setMessages",
        "setInput",
        "setEditingMessageIndex",
        "setError",
        "setToast",
      ].map((name) => [name, vi.fn()])
    );

    const { result } = renderHook(() =>
      useOpenWorkspaceSharedConversation({ ...setters, t: (key) => key })
    );

    await result.current.openWorkspaceSharedConversation("7", "44");

    expect(getWorkspaceSharedConversation).toHaveBeenCalledWith(7, 44);
    expect(setters.setShowShareManager).toHaveBeenCalledWith(false);
    expect(setters.setReadOnlyConversation).toHaveBeenCalledWith(true);
    expect(setters.setShowWorkspaceComments).toHaveBeenCalledWith(true);
    expect(setters.setSelectedWorkspaceId).toHaveBeenCalledWith(7);
    expect(setters.setConversationId).toHaveBeenCalledWith(44);
    expect(setters.setSelectedModel).toHaveBeenCalledWith("");
    expect(setters.setMessages).toHaveBeenCalledWith([
      expect.objectContaining({
        role: "user",
        text: "Hello",
        sources: ["source"],
        feedback: null,
        isBookmarked: false,
      }),
    ]);
    expect(setters.setInput).toHaveBeenCalledWith("");
    expect(setters.setError).toHaveBeenCalledWith("");
  });

  it("shows the translated API error", async () => {
    getWorkspaceSharedConversation.mockRejectedValue({
      response: { data: { detail: "Not shared" } },
    });

    const setToast = vi.fn();
    const { result } = renderHook(() =>
      useOpenWorkspaceSharedConversation({
        ...Object.fromEntries(
          [
            "setShowShareManager",
            "setReadOnlyConversation",
            "setShowWorkspaceComments",
            "setWorkspaceShare",
            "setSelectedWorkspaceId",
            "setConversationId",
            "setConversationSummary",
            "setConversationSummaryUpdatedAt",
            "setSelectedAssistantId",
            "setSelectedFolderId",
            "setSelectedProjectId",
            "setSelectedModel",
            "setMessages",
            "setInput",
            "setEditingMessageIndex",
            "setError",
          ].map((name) => [name, vi.fn()])
        ),
        setToast,
        t: (key) => key,
      })
    );

    await waitFor(() => result.current);
    await result.current.openWorkspaceSharedConversation(7, 44);

    expect(setToast).toHaveBeenCalledWith({
      message: "Not shared",
      type: "error",
    });
  });
});
