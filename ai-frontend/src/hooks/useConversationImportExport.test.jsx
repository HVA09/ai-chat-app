import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import useConversationImportExport from "./useConversationImportExport";
import {
  exportConversation,
  importConversation,
  importConversations,
} from "../lib/conversationsApi";

vi.mock("../lib/conversationsApi", () => ({
  exportConversation: vi.fn(),
  importConversation: vi.fn(),
  importConversations: vi.fn(),
}));

function createProps(overrides = {}) {
  return {
    conversationId: 7,
    loading: false,
    selectedWorkspaceId: 2,
    refreshConversations: vi.fn(),
    openConversation: vi.fn(),
    setShowArchivedConversations: vi.fn(),
    setShowTrashConversations: vi.fn(),
    setConversationSearch: vi.fn(),
    setSelectedTagId: vi.fn(),
    setSelectedFolderId: vi.fn(),
    setSelectedProjectId: vi.fn(),
    setSelectedConversationIds: vi.fn(),
    setToast: vi.fn(),
    t: (key, vars) => (vars ? `${key}:${vars.count}` : key),
    ...overrides,
  };
}

function fileFromPayload(payload) {
  const file = new File([JSON.stringify(payload)], "conversation.json", {
    type: "application/json",
  });
  return file;
}

describe("useConversationImportExport", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("rejects oversized imports and missing workspace context", async () => {
    const props = createProps();
    const { result, rerender } = renderHook((value) => useConversationImportExport(value), {
      initialProps: props,
    });

    await act(async () => {
      const file = new File([new Uint8Array(10 * 1024 * 1024 + 1)], "large.json");
      await result.current.handleImportConversation(file);
    });
    expect(props.setToast).toHaveBeenCalledWith({
      message: "importConversationTooLarge",
      type: "error",
    });

    props.selectedWorkspaceId = null;
    rerender(props);
    await act(async () => {
      await result.current.handleImportConversation(fileFromPayload({ messages: [{ role: "user" }] }));
    });
    expect(props.setToast).toHaveBeenLastCalledWith({
      message: "importConversationError",
      type: "error",
    });
  });

  it("imports a bulk export, resets filters, refreshes, and opens the first conversation", async () => {
    importConversations.mockResolvedValue({
      conversation_ids: [101, 102],
      imported_count: 2,
    });
    const props = createProps();
    const { result } = renderHook(() => useConversationImportExport(props));

    await act(async () => {
      await result.current.handleImportConversation(
        fileFromPayload({
          version: 1,
          conversations: [{ id: 1 }, { id: 2 }],
        })
      );
    });

    expect(importConversations).toHaveBeenCalledWith(2, {
      version: 1,
      conversations: [{ id: 1 }, { id: 2 }],
    });
    expect(props.setSelectedConversationIds).toHaveBeenCalledWith([]);
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false,
      null,
      2,
      null,
      "",
      false,
      null
    );
    expect(props.openConversation).toHaveBeenCalledWith(101);
    expect(props.setToast).toHaveBeenLastCalledWith({
      message: "bulkImportSuccess:2",
      type: "success",
    });
  });

  it("imports a single conversation with preserved metadata and opens it", async () => {
    importConversation.mockResolvedValue({
      id: 55,
      folder_id: 9,
      project_id: 12,
    });
    const props = createProps();
    const { result } = renderHook(() => useConversationImportExport(props));

    await act(async () => {
      await result.current.handleImportConversation(
        fileFromPayload({
          title: "Imported",
          messages: [{ role: "user", text: "hello" }],
          folder_id: 4,
          project_id: 8,
          assistant_id: 3,
          ai_model: "model-x",
        })
      );
    });

    expect(importConversation).toHaveBeenCalledWith(2, {
      title: "Imported",
      messages: [{ role: "user", text: "hello" }],
      folder_id: 4,
      project_id: 8,
      assistant_id: 3,
      ai_model: "model-x",
    });
    expect(props.setSelectedFolderId).toHaveBeenCalledWith(9);
    expect(props.setSelectedProjectId).toHaveBeenCalledWith(12);
    expect(props.refreshConversations).toHaveBeenCalledWith(
      false,
      9,
      2,
      12,
      "",
      false,
      null
    );
    expect(props.openConversation).toHaveBeenCalledWith(55);
  });

  it("rejects malformed import payloads", async () => {
    const props = createProps();
    const { result } = renderHook(() => useConversationImportExport(props));

    await act(async () => {
      await result.current.handleImportConversation(
        fileFromPayload({ version: 2, conversations: [] })
      );
    });

    expect(props.setToast).toHaveBeenLastCalledWith({
      message: "importConversationInvalidFile",
      type: "error",
    });
    expect(importConversations).not.toHaveBeenCalled();
    expect(importConversation).not.toHaveBeenCalled();
  });

  it("exports the active conversation and handles export failures", async () => {
    const props = createProps();
    const { result, rerender } = renderHook(
      (value) => useConversationImportExport(value),
      { initialProps: props }
    );

    exportConversation.mockResolvedValue(undefined);
    await act(async () => {
      await result.current.handleExportConversation("json");
    });
    expect(exportConversation).toHaveBeenCalledWith(7, "json");
    expect(props.setToast).toHaveBeenLastCalledWith({
      message: "exportConversationSuccess",
      type: "success",
    });

    exportConversation.mockRejectedValue({
      response: { data: { detail: "backend failed" } },
    });
    await act(async () => {
      await result.current.handleExportConversation("markdown");
    });
    expect(props.setToast).toHaveBeenLastCalledWith({
      message: "backend failed",
      type: "error",
    });

    props.conversationId = null;
    rerender(props);
    await act(async () => {
      await result.current.handleExportConversation();
    });
    expect(exportConversation).toHaveBeenCalledTimes(2);
  });
});
