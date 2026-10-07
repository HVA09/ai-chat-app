import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useChatAttachments from "./useChatAttachments";
import { deleteFile, uploadFile } from "../lib/filesApi";

vi.mock("../lib/filesApi", () => ({
  uploadFile: vi.fn(),
  deleteFile: vi.fn(),
}));

const t = (key) => key;

function createFile(name = "note.txt", size = 4) {
  return new File([new Uint8Array(size)], name, { type: "text/plain" });
}

describe("useChatAttachments", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uploads valid files and resets its state", async () => {
    uploadFile.mockResolvedValue({
      id: 12,
      original_filename: "note.txt",
      content_type: "text/plain",
      size_bytes: 4,
    });

    const setToast = vi.fn();
    const { result } = renderHook(() =>
      useChatAttachments({
        conversationId: 7,
        selectedWorkspaceId: 2,
        selectedProjectId: 3,
        loading: false,
        readOnlyConversation: false,
        editingMessageIndex: null,
        setToast,
        t,
      })
    );

    await act(async () => {
      await result.current.handleAttachFiles([createFile()]);
    });

    expect(uploadFile).toHaveBeenCalledWith(
      expect.any(File),
      undefined,
      7,
      2,
      3
    );
    expect(result.current.chatAttachments).toEqual([
      {
        id: 12,
        original_filename: "note.txt",
        content_type: "text/plain",
        size_bytes: 4,
      },
    ]);
    expect(result.current.chatAttachmentUploading).toBe(false);

    act(() => {
      result.current.resetChatAttachments();
    });

    expect(result.current.chatAttachments).toEqual([]);
  });

  it("removes an attachment after a successful delete", async () => {
    deleteFile.mockResolvedValue({});

    const { result } = renderHook(() =>
      useChatAttachments({
        conversationId: 7,
        selectedWorkspaceId: null,
        selectedProjectId: null,
        loading: false,
        readOnlyConversation: false,
        editingMessageIndex: null,
        setToast: vi.fn(),
        t,
      })
    );

    uploadFile.mockResolvedValue({
      id: 21,
      original_filename: "image.png",
      content_type: "image/png",
      size_bytes: 8,
    });

    await act(async () => {
      await result.current.handleAttachFiles([
        new File([new Uint8Array(8)], "image.png", { type: "image/png" }),
      ]);
    });

    await act(async () => {
      await result.current.handleRemoveAttachment(21);
    });

    expect(deleteFile).toHaveBeenCalledWith(21);
    expect(result.current.chatAttachments).toEqual([]);
  });
});
