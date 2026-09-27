import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ModelCompareDialog from "./ModelCompareDialog";
import { compareChatModels } from "../lib/chatApi";

vi.mock("../lib/chatApi", () => ({
  compareChatModels: vi.fn(),
}));

vi.mock("../lib/errors", () => ({
  getErrorMessage: vi.fn((error, fallback) => error?.response?.data?.detail || fallback),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) =>
      ({
        "modelCompare.title": "Compare models",
        "modelCompare.hint": "Compare two models",
        "modelCompare.needTwoModels": "Need two models",
        "modelCompare.promptPlaceholder": "Prompt",
        "modelCompare.modelA": "Model A",
        "modelCompare.modelB": "Model B",
        "modelCompare.cancel": "Cancel",
        "modelCompare.compare": "Compare",
        "modelCompare.running": "Comparing...",
        "modelCompare.error": "Could not compare models",
      })[key] ?? key,
  }),
}));

describe("ModelCompareDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    compareChatModels.mockResolvedValue({
      results: [
        { model: "alpha", latency_ms: 100, text: "A" },
        { model: "beta", latency_ms: 120, text: "B" },
      ],
    });
  });

  it("renders comparison results", async () => {
    const user = userEvent.setup();
    render(
      <ModelCompareDialog
        models={[
          { id: "alpha", label: "Alpha" },
          { id: "beta", label: "Beta" },
        ]}
      />
    );

    await user.type(screen.getByPlaceholderText("Prompt"), "Hello");
    await user.click(screen.getByRole("button", { name: "Compare" }));

    expect(await screen.findByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
  });

  it("shows a global toast when comparison fails", async () => {
    const user = userEvent.setup();
    compareChatModels.mockRejectedValueOnce({
      response: { data: { detail: "Comparison denied" } },
    });
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    render(
      <ModelCompareDialog
        models={[
          { id: "alpha", label: "Alpha" },
          { id: "beta", label: "Beta" },
        ]}
      />
    );

    await user.type(screen.getByPlaceholderText("Prompt"), "Hello");
    await user.click(screen.getByRole("button", { name: "Compare" }));

    await waitFor(() => {
      expect(
        dispatchSpy.mock.calls.some(
          ([event]) =>
            event.type === "app:toast" &&
            event.detail?.message === "Comparison denied" &&
            event.detail?.type === "error"
        )
      ).toBe(true);
    });

    expect(screen.queryByText("Comparison denied")).not.toBeInTheDocument();
    dispatchSpy.mockRestore();
  });
});
