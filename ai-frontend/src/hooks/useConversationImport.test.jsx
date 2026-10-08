import { renderHook, act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useConversationImport from "./useConversationImport";

vi.mock("../lib/conversationsApi", () => ({
  importConversation: vi.fn(),
  importConversations: vi.fn(),
}));

import {
  importConversation,
  importConversations,
} from "../lib/conversationsApi";

const makeFile = (value) => ({
  size: new Blob([value]).size,
  text: vi.fn(async () => value),
});

describe("useConversationImport", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("rejects invalid JSON without importing", async () => {
    const setToast = vi.fn();
    const props = {
      selectedWorkspaceId: 1,
      t: (key) => key,
      setToast,
      setShowArchivedConversations: vi.fn(),
      setShowTrashConversations: vi.fn(),
      setConversationSearch: vi.fn(),
      setSelectedTagId: vi.fn(),
      setSelectedFolderId: vi.fn(),
      setSelectedProjectId: vi.fn(),
      setSelectedConversationIds: vi.fn(),
      refreshConversations: vi.fn(),
      openConversation: vi.fn(),
    };
    const { result } = renderHook(() => useConversationImport(props));

    await act(async () => {
      await result.current.handleImportConversation(makeFile("{invalid"));
    });

    expect(importConversation).not.toHaveBeenCalled();
    expect(importConversations).not.toHaveBeenCalled();
    expect(setToast).toHaveBeenCalledWith({
      message: "importConversationInvalidFile",
      type: "error",
    });
  });

  it("imports a single conversation and opens it", async () => {
    importConversation.mockResolvedValue({
      id: 42,
      folder_id: 7,
      project_id: 9,
    });

    const setToast = vi.fn();
    const refreshConversations = vi.fn();
    const openConversation = vi.fn();
    const props = {
      selectedWorkspaceId: 3,
      t: (key) => key,
      setToast,
      setShowArchivedConversations: vi.fn(),
      setShowTrashConversations: vi.fn(),
      setConversationSearch: vi.fn(),
      setSelectedTagId: vi.fn(),
      setSelectedFolderId: vi.fn(),
      setSelectedProjectId: vi.fn(),
      setSelectedConversationIds: vi.fn(),
      refreshConversations,
      openConversation,
    };
    const { result } = renderHook(() => useConversationImport(props));

    await act(async () => {
      await result.current.handleImportConversation(
        makeFile(JSON.stringify({ title: "Imported", messages: [{ role: "user", content: "Hi" }] }))
      );
    });

    expect(importConversation).toHaveBeenCalledWith(3, {
      title: "Imported",
      messages: [{ role: "user", content: "Hi" }],
      folder_id: null,
      project_id: null,
      assistant_id: null,
      ai_model: null,
    });
    expect(refreshConversations).toHaveBeenCalledWith(
      false,
      7,
      3,
      9,
      "",
      false,
      null
    );
    expect(openConversation).toHaveBeenCalledWith(42);
    expect(setToast).toHaveBeenCalledWith({
      message: "importConversationSuccess",
      type: "success",
    });
  });
});
