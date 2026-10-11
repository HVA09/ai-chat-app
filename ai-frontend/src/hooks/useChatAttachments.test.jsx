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

  it("isolates attachment uploads across a draft reset while a newer upload is active", async () => {
    let resolveOldUpload;
    let resolveNewUpload;
    uploadFile
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOldUpload = resolve; }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveNewUpload = resolve; }));

    const setToast = vi.fn();
    const baseProps = {
      selectedWorkspaceId: null,
      selectedProjectId: null,
      loading: false,
      readOnlyConversation: false,
      editingMessageIndex: null,
      setToast,
      t,
    };
    const { result, rerender } = renderHook(
      ({ conversationId }) => useChatAttachments({ ...baseProps, conversationId }),
      { initialProps: { conversationId: 7 } }
    );

    let oldUpload;
    await act(async () => {
      oldUpload = result.current.handleAttachFiles([createFile("old.txt")]);
    });
    expect(result.current.chatAttachmentUploading).toBe(true);
    expect(uploadFile).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.resetChatAttachments();
      rerender({ conversationId: 8 });
    });

    let newUpload;
    await act(async () => {
      newUpload = result.current.handleAttachFiles([createFile("new.txt")]);
    });
    expect(result.current.chatAttachmentUploading).toBe(true);
    expect(uploadFile).toHaveBeenCalledTimes(2);

    await act(async () => {
      resolveOldUpload({
        id: 12,
        original_filename: "old.txt",
        content_type: "text/plain",
        size_bytes: 4,
      });
      await oldUpload;
    });
    expect(result.current.chatAttachments).toEqual([]);
    expect(result.current.chatAttachmentUploading).toBe(true);
    expect(setToast).not.toHaveBeenCalled();

    await act(async () => {
      resolveNewUpload({
        id: 13,
        original_filename: "new.txt",
        content_type: "text/plain",
        size_bytes: 4,
      });
      await newUpload;
    });

    expect(uploadFile).toHaveBeenNthCalledWith(1, expect.any(File), undefined, 7, null, null);
    expect(uploadFile).toHaveBeenNthCalledWith(2, expect.any(File), undefined, 8, null, null);
    expect(result.current.chatAttachments).toEqual([
      {
        id: 13,
        original_filename: "new.txt",
        content_type: "text/plain",
        size_bytes: 4,
      },
    ]);
    expect(result.current.chatAttachmentUploading).toBe(false);
    expect(setToast).toHaveBeenCalledWith({ message: "app.attachmentsReady", type: "success" });
  });

  it("does not restore a removed attachment after the draft is reset", async () => {
    uploadFile.mockResolvedValue({
      id: 21,
      original_filename: "old.txt",
      content_type: "text/plain",
      size_bytes: 4,
    });
    let rejectDelete;
    deleteFile.mockImplementationOnce(
      () => new Promise((_resolve, reject) => { rejectDelete = reject; })
    );

    const setToast = vi.fn();
    const baseProps = {
      selectedWorkspaceId: null,
      selectedProjectId: null,
      loading: false,
      readOnlyConversation: false,
      editingMessageIndex: null,
      setToast,
      t,
    };
    const { result, rerender } = renderHook(
      ({ conversationId }) => useChatAttachments({ ...baseProps, conversationId }),
      { initialProps: { conversationId: 7 } }
    );

    await act(async () => {
      await result.current.handleAttachFiles([createFile("old.txt")]);
    });
    expect(result.current.chatAttachments).toHaveLength(1);
    const toastCountBeforeRemove = setToast.mock.calls.length;

    let removePromise;
    await act(async () => {
      removePromise = result.current.handleRemoveAttachment(21);
    });
    expect(result.current.chatAttachments).toEqual([]);

    act(() => {
      result.current.resetChatAttachments();
      rerender({ conversationId: 8 });
    });

    await act(async () => {
      rejectDelete(new Error("delete failed"));
      await removePromise;
    });

    expect(result.current.chatAttachments).toEqual([]);
    expect(setToast).toHaveBeenCalledTimes(toastCountBeforeRemove);
  });
});
