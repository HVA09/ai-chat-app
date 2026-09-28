import { describe, expect, it, vi, beforeEach } from "vitest";

const api = vi.hoisted(() => ({
  post: vi.fn(),
  get: vi.fn(),
}));

vi.mock("./api", () => ({ default: api }));

describe("filesApi regression coverage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uploads a file with conversation/workspace/project scope and lets axios set multipart headers", async () => {
    api.post.mockResolvedValue({ data: { id: 42, original_filename: "notes.txt" } });

    const { uploadFile } = await import("./filesApi");
    const file = new File(["hello"], "notes.txt", { type: "text/plain" });
    await uploadFile(file, undefined, 7, 3, 9);

    expect(api.post).toHaveBeenCalledTimes(1);
    const [url, formData, config] = api.post.mock.calls[0];

    expect(url).toBe("/files/upload");
    expect(formData).toBeInstanceOf(FormData);
    expect(formData.get("file")).toBe(file);
    expect(config.params).toEqual({
      conversation_id: 7,
      workspace_id: 3,
      project_id: 9,
    });
    expect(config.headers).toBeUndefined();
  });

  it("preserves the current conversation scope when IDs are omitted", async () => {
    api.post.mockResolvedValue({ data: { id: 43 } });

    const { uploadFile } = await import("./filesApi");
    const file = new File(["hello"], "notes.txt", { type: "text/plain" });
    await uploadFile(file);

    const [, , config] = api.post.mock.calls[0];
    expect(config.params).toEqual({});
  });

  it("sends file_ids in the regular chat payload", async () => {
    api.post.mockResolvedValue({ data: { id: 99 } });

    const { sendChatMessage } = await import("./chatApi");
    await sendChatMessage("analyze this", 12, null, 3, 9, "model-a", [42, 43]);

    expect(api.post).toHaveBeenCalledWith("/chat", {
      message: "analyze this",
      conversation_id: 12,
      assistant_id: null,
      workspace_id: 3,
      project_id: 9,
      model: "model-a",
      file_ids: [42, 43],
    });
  });
});
