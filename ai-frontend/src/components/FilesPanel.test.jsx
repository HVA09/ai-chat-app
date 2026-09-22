import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import FilesPanel from "./FilesPanel";
import { listFiles, uploadFile } from "../lib/filesApi";

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
  getErrorMessage: (_error, fallback) => fallback,
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
    })[key] ?? key,
  }),
}));

describe("FilesPanel project knowledge", () => {
  afterEach(() => {
    vi.clearAllMocks();
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
});
