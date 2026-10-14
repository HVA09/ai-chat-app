import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import useConversationExport from "./useConversationExport";

vi.mock("../lib/conversationsApi", () => ({
  exportConversation: vi.fn(),
}));

import { exportConversation } from "../lib/conversationsApi";

const makeProps = (overrides = {}) => ({
  conversationId: 12,
  loading: false,
  setToast: vi.fn(),
  t: (key) => key,
  ...overrides,
});

describe("useConversationExport", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("exports the current conversation as Markdown by default", async () => {
    const props = makeProps();
    exportConversation.mockResolvedValueOnce({});

    const { result } = renderHook(() => useConversationExport(props));
    await act(async () => {
      await result.current.handleExportConversation();
    });

    expect(exportConversation).toHaveBeenCalledWith(12, "markdown");
    expect(props.setToast).toHaveBeenCalledWith({
      message: "exportConversationSuccess",
      type: "success",
    });
  });

  it("passes through the requested export format", async () => {
    const props = makeProps();
    exportConversation.mockResolvedValueOnce({});

    const { result } = renderHook(() => useConversationExport(props));
    await act(async () => {
      await result.current.handleExportConversation("json");
    });

    expect(exportConversation).toHaveBeenCalledWith(12, "json");
    expect(props.setToast).toHaveBeenCalledWith({
      message: "exportConversationSuccess",
      type: "success",
    });
  });

  it("does not export when there is no active conversation or the app is loading", async () => {
    const noConversation = renderHook(() =>
      useConversationExport(makeProps({ conversationId: null }))
    );
    await act(async () => {
      await noConversation.result.current.handleExportConversation();
    });

    const loading = renderHook(() =>
      useConversationExport(makeProps({ loading: true }))
    );
    await act(async () => {
      await loading.result.current.handleExportConversation();
    });

    expect(exportConversation).not.toHaveBeenCalled();
  });

  it("shows the API error detail when export fails", async () => {
    const props = makeProps();
    exportConversation.mockRejectedValueOnce({
      response: { data: { detail: "export denied" } },
    });

    const { result } = renderHook(() => useConversationExport(props));
    await act(async () => {
      await result.current.handleExportConversation("json");
    });

    expect(props.setToast).toHaveBeenCalledWith({
      message: "export denied",
      type: "error",
    });
  });

  it("uses the translated fallback when export fails without API detail", async () => {
    const props = makeProps();
    exportConversation.mockRejectedValueOnce(new Error("offline"));

    const { result } = renderHook(() => useConversationExport(props));
    await act(async () => {
      await result.current.handleExportConversation();
    });

    expect(props.setToast).toHaveBeenCalledWith({
      message: "exportConversationError",
      type: "error",
    });
  });
});
