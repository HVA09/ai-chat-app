import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import useConversationBranching from "./useConversationBranching";
import { branchConversation } from "../lib/conversationsApi";

vi.mock("../lib/conversationsApi", () => ({
  branchConversation: vi.fn(),
}));

describe("useConversationBranching", () => {
  const createProps = (overrides = {}) => ({
    conversationId: 12,
    conversationSearch: "search",
    loading: false,
    openConversation: vi.fn().mockResolvedValue(undefined),
    readOnlyConversation: false,
    refreshConversations: vi.fn().mockResolvedValue(undefined),
    selectedFolderId: 3,
    selectedProjectId: 4,
    selectedTagId: 5,
    selectedWorkspaceId: 6,
    setToast: vi.fn(),
    showArchivedConversations: true,
    showTrashConversations: false,
    t: (key) => key,
    ...overrides,
  });

  it("branches from the message and opens the created conversation", async () => {
    branchConversation.mockResolvedValue({ id: 99 });
    const props = createProps();
    const { result } = renderHook(() => useConversationBranching(props));

    await result.current.handleBranchConversation(7);

    expect(branchConversation).toHaveBeenCalledWith(12, 8);
    expect(props.refreshConversations).toHaveBeenCalledWith(
      true,
      3,
      6,
      4,
      "search",
      false,
      5
    );
    expect(props.openConversation).toHaveBeenCalledWith(99);
    expect(props.setToast).toHaveBeenCalledWith({
      message: "app.branchConversationSuccess",
      type: "success",
    });
  });

  it("surfaces the backend error without opening a new conversation", async () => {
    branchConversation.mockRejectedValue({
      response: { data: { detail: "Branch failed" } },
    });
    const props = createProps();
    const { result } = renderHook(() => useConversationBranching(props));

    await result.current.handleBranchConversation(2);

    expect(props.openConversation).not.toHaveBeenCalled();
    expect(props.setToast).toHaveBeenCalledWith({
      message: "Branch failed",
      type: "error",
    });
  });

  it("does nothing when branching is not allowed", async () => {
    const props = createProps({ loading: true });
    const { result } = renderHook(() => useConversationBranching(props));

    await result.current.handleBranchConversation(2);

    expect(branchConversation).not.toHaveBeenCalled();
    expect(props.refreshConversations).not.toHaveBeenCalled();
  });
});
