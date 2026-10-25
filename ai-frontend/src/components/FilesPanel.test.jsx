import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import FilesPanel from "./FilesPanel";
import {
  attachFileToConversation,
  deleteFile,
  indexImageForRag,
  listFiles,
  uploadFile,
} from "../lib/filesApi";

vi.mock("../lib/filesApi", () => ({
  attachFileToConversation: vi.fn(),
  deleteFile: vi.fn(),
  detachFileFromConversation: vi.fn(),
  downloadFile: vi.fn(),
  fetchFileBlob: vi.fn(),
  indexImageForRag: vi.fn(),
  listFiles: vi.fn().mockResolvedValue([]),
  uploadFile: vi.fn().mockResolvedValue({}),
}));

vi.mock("../lib/errors", () => ({
  getErrorMessage: (error, fallback) => error?.response?.data?.detail || fallback,
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) => ({
      "files.title": "Files",
      "files.workspaceTitle": "Workspace knowledge",
      "files.projectTitle": "Project knowledge",
      "files.myFiles": "My files",
      "files.workspaceFiles": "Workspace knowledge",
      "files.projectFiles": "Project knowledge",
      "files.dropHint": "Drop a file here",
      "files.projectDropHint": "Upload a file to project knowledge",
      "files.typesHint": "Files",
      "files.noFiles": "No files",
      "files.listError": "Could not load files",
      "files.deleteError": "Could not delete file",
      "files.uploadErrorForFile": "Could not upload the file {{name}}",
      "files.attachmentError": "Could not update the file attachment",
      "files.attach": "Attach",
      "files.detach": "Detach",
      "files.confirmDelete": "Delete this file?",
      "files.delete": "Delete",
    })[key] ?? key,
  }),
}));

describe("FilesPanel project knowledge", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows a global toast when loading files fails", async () => {
    listFiles.mockRejectedValue({
      response: { data: { detail: "Access denied" } },
    });
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    render(<FilesPanel onClose={vi.fn()} />);

    await waitFor(() => {
      expect(
        dispatchSpy.mock.calls.some(
          ([event]) =>
            event.type === "app:toast" &&
            event.detail?.message === "Access denied" &&
            event.detail?.type === "error"
        )
      ).toBe(true);
    });

    dispatchSpy.mockRestore();
  });

  it("shows a global toast when deleting a file fails", async () => {
    listFiles.mockResolvedValue([
      {
        id: 11,
        original_filename: "notes.txt",
        content_type: "text/plain",
        size: 100,
        is_attached: false,
        is_ai_indexed: false,
        can_delete: true,
      },
    ]);
    deleteFile.mockRejectedValue({
      response: { data: { detail: "Delete denied" } },
    });
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();

    render(<FilesPanel onClose={vi.fn()} />);

    await user.click(await screen.findByTitle("Delete"));

    await waitFor(() => {
      expect(
        dispatchSpy.mock.calls.some(
          ([event]) =>
            event.type === "app:toast" &&
            event.detail?.message === "Delete denied" &&
            event.detail?.type === "error"
        )
      ).toBe(true);
    });

    confirmSpy.mockRestore();
    dispatchSpy.mockRestore();
  });

  it("shows a global toast when uploading a file fails", async () => {
    const user = userEvent.setup();
    const { container } = render(<FilesPanel onClose={vi.fn()} />);
    uploadFile.mockRejectedValueOnce({
      response: { data: { detail: "Upload denied" } },
    });
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    const input = container.querySelector('input[type="file"]');
    const file = new File(["data"], "notes.txt", { type: "text/plain" });

    await user.upload(input, file);

    await waitFor(() => {
      expect(
        dispatchSpy.mock.calls.some(
          ([event]) =>
            event.type === "app:toast" &&
            event.detail?.message === "Upload denied" &&
            event.detail?.type === "error"
        )
      ).toBe(true);
    });

    dispatchSpy.mockRestore();
  });

  it("shows a global toast when attachment update fails", async () => {
    const user = userEvent.setup();
    attachFileToConversation.mockRejectedValueOnce({
      response: { data: { detail: "Attach denied" } },
    });
    listFiles.mockResolvedValueOnce([
      {
        id: 12,
        original_filename: "notes.txt",
        content_type: "text/plain",
        size: 100,
        is_attached: false,
        is_ai_indexed: false,
        can_delete: false,
      },
    ]);
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    render(<FilesPanel onClose={vi.fn()} conversationId={55} />);

    await user.click(await screen.findByTitle("Attach"));

    await waitFor(() => {
      expect(
        dispatchSpy.mock.calls.some(
          ([event]) =>
            event.type === "app:toast" &&
            event.detail?.message === "Attach denied" &&
            event.detail?.type === "error"
        )
      ).toBe(true);
    });

    dispatchSpy.mockRestore();
  });

  it("loads project knowledge files with the selected project id", async () => {
    const user = userEvent.setup();

    render(
      <FilesPanel
        onClose={vi.fn()}
        workspaceId={7}
        projectId={42}
      />
    );

    await user.click(screen.getByRole("button", { name: "Project knowledge" }));

    await waitFor(() => {
      expect(listFiles).toHaveBeenLastCalledWith(null, false, 7, 42);
    });

    expect(screen.getByText("Upload a file to project knowledge")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Project knowledge" })).toBeInTheDocument();
  });

  it("uploads files into project knowledge", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <FilesPanel
        onClose={vi.fn()}
        workspaceId={7}
        projectId={42}
      />
    );

    await user.click(screen.getByRole("button", { name: "Project knowledge" }));

    const input = container.querySelector('input[type="file"]');
    const file = new File(["project data"], "knowledge.txt", { type: "text/plain" });

    await user.upload(input, file);

    await waitFor(() => {
      expect(uploadFile).toHaveBeenCalledWith(
        file,
        expect.any(Function),
        null,
        7,
        42
      );
    });
  });

  it("ignores stale file-list responses after the selected conversation changes", async () => {
    listFiles.mockReset();
    let resolveOlder;
    let resolveCurrent;
    listFiles
      .mockImplementationOnce(
        () => new Promise((resolve) => { resolveOlder = resolve; })
      )
      .mockImplementationOnce(
        () => new Promise((resolve) => { resolveCurrent = resolve; })
      );

    const oldFile = {
      id: 71,
      original_filename: "old-conversation.txt",
      content_type: "text/plain",
      size_bytes: 4,
      created_at: "2026-10-17T10:00:00Z",
      workspace_id: null,
      project_id: null,
      is_attached: false,
      is_ai_indexed: false,
      can_delete: false,
    };
    const currentFile = {
      ...oldFile,
      id: 72,
      original_filename: "current-conversation.txt",
    };
    const { rerender } = render(
      <FilesPanel onClose={vi.fn()} conversationId={11} />
    );

    await waitFor(() => expect(listFiles).toHaveBeenCalledTimes(1));
    rerender(<FilesPanel onClose={vi.fn()} conversationId={22} />);
    await waitFor(() => expect(listFiles).toHaveBeenCalledTimes(2));

    await act(async () => {
      resolveCurrent([currentFile]);
    });
    expect(await screen.findByText("current-conversation.txt")).toBeInTheDocument();

    await act(async () => {
      resolveOlder([oldFile]);
    });
    expect(screen.getByText("current-conversation.txt")).toBeInTheDocument();
    expect(screen.queryByText("old-conversation.txt")).not.toBeInTheDocument();
  });

  it("does not show an error from an obsolete file-list request", async () => {
    listFiles.mockReset();
    let rejectOlder;
    let resolveCurrent;
    listFiles
      .mockImplementationOnce(
        () => new Promise((_resolve, reject) => { rejectOlder = reject; })
      )
      .mockImplementationOnce(
        () => new Promise((resolve) => { resolveCurrent = resolve; })
      );

    const setDispatchSpy = vi.spyOn(window, "dispatchEvent");
    const { rerender } = render(
      <FilesPanel onClose={vi.fn()} conversationId={11} />
    );

    await waitFor(() => expect(listFiles).toHaveBeenCalledTimes(1));
    rerender(<FilesPanel onClose={vi.fn()} conversationId={22} />);
    await waitFor(() => expect(listFiles).toHaveBeenCalledTimes(2));

    await act(async () => {
      resolveCurrent([]);
    });
    await act(async () => {
      rejectOlder({ response: { data: { detail: "Stale request denied" } } });
    });

    expect(
      setDispatchSpy.mock.calls.some(
        ([event]) =>
          event.type === "app:toast" &&
          event.detail?.message === "Stale request denied"
      )
    ).toBe(false);
    setDispatchSpy.mockRestore();
  });

  it("does not refresh the old conversation when an upload finishes after switching conversations", async () => {
    listFiles.mockReset().mockResolvedValue([]);
    uploadFile.mockReset();
    let resolveUpload;
    uploadFile.mockImplementationOnce(
      () => new Promise((resolve) => { resolveUpload = resolve; })
    );

    const user = userEvent.setup();
    const { container, rerender } = render(
      <FilesPanel onClose={vi.fn()} conversationId={11} />
    );

    await waitFor(() => expect(listFiles).toHaveBeenCalledTimes(1));
    const input = container.querySelector('input[type="file"]');
    const file = new File(["old scope"], "upload.txt", { type: "text/plain" });
    await user.upload(input, file);
    await waitFor(() => expect(uploadFile).toHaveBeenCalledTimes(1));

    rerender(<FilesPanel onClose={vi.fn()} conversationId={22} />);
    await waitFor(() => expect(listFiles).toHaveBeenCalledTimes(2));

    await act(async () => {
      resolveUpload({
        id: 99,
        original_filename: "upload.txt",
        content_type: "text/plain",
        size_bytes: 9,
      });
      await Promise.resolve();
    });

    await waitFor(() => expect(screen.getByText("100%")).toBeInTheDocument());
    expect(listFiles).toHaveBeenCalledTimes(2);
  });


  it("keeps image indexing retry available after provider failure", async () => {
    const file = {
      id: 89,
      original_filename: "retry-chart.png",
      content_type: "image/png",
      size_bytes: 42,
      created_at: "2026-10-25T12:00:00Z",
      workspace_id: null,
      project_id: null,
      is_attached: false,
      is_ai_indexed: false,
      can_delete: false,
    };
    listFiles
      .mockReset()
      .mockResolvedValueOnce([file])
      .mockResolvedValueOnce([{ ...file, is_ai_indexed: true }]);
    indexImageForRag
      .mockReset()
      .mockRejectedValueOnce({
        response: { data: { detail: "Embedding provider unavailable" } },
      })
      .mockResolvedValueOnce({ id: file.id, is_ai_indexed: true });

    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    const user = userEvent.setup();

    try {
      render(<FilesPanel onClose={vi.fn()} />);
      const indexButton = await screen.findByTitle("files.indexImageForAi");
      expect(indexButton).not.toBeDisabled();

      await user.click(indexButton);
      await waitFor(() => {
        expect(indexImageForRag).toHaveBeenCalledTimes(1);
        expect(indexButton).not.toBeDisabled();
      });
      expect(listFiles).toHaveBeenCalledTimes(1);
      expect(
        dispatchSpy.mock.calls.some(
          ([event]) =>
            event.type === "app:toast" &&
            event.detail?.message === "Embedding provider unavailable" &&
            event.detail?.type === "error"
        )
      ).toBe(true);

      await user.click(indexButton);
      await waitFor(() => expect(indexImageForRag).toHaveBeenCalledTimes(2));
      await waitFor(() => expect(listFiles).toHaveBeenCalledTimes(2));

      const indexedButton = await screen.findByTitle("files.imageIndexed");
      expect(indexedButton).toBeDisabled();
    } finally {
      dispatchSpy.mockRestore();
    }
  });


});
