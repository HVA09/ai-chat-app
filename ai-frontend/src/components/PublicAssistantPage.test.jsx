import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PublicAssistantPage from "./PublicAssistantPage";
import {
  duplicatePublicAssistant,
  getPublicAssistant,
} from "../lib/publicAssistantsApi";

vi.mock("../lib/publicAssistantsApi", () => ({
  duplicatePublicAssistant: vi.fn(),
  getPublicAssistant: vi.fn(),
}));

vi.mock("../lib/errors", () => ({
  getErrorMessage: vi.fn((error, fallback) => error?.response?.data?.detail || fallback),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) =>
      ({
        "publicAssistant.backToApp": "Back to app",
        "publicAssistant.loadError": "Could not load assistant",
        "publicAssistant.loginRequired": "Please log in first",
        "publicAssistant.duplicateError": "Could not duplicate assistant",
        "publicAssistant.duplicating": "Duplicating...",
        "publicAssistant.duplicate": "Duplicate",
        "publicAssistant.noDescription": "No description",
        "publicAssistant.safeNotice": "Safe",
        "publicAssistant.notFoundTitle": "Assistant not found",
      })[key] ?? key,
  }),
}));

describe("PublicAssistantPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, "", "/public-assistant/demo-token");
    getPublicAssistant.mockResolvedValue({
      name: "Demo assistant",
      description: "Demo description",
    });
    duplicatePublicAssistant.mockResolvedValue({});
  });

  afterEach(() => {
    window.history.pushState({}, "", "/");
  });

  it("renders the public assistant", async () => {
    render(<PublicAssistantPage />);

    expect(await screen.findByRole("heading", { name: "Demo assistant" })).toBeInTheDocument();
    expect(screen.getByText("Demo description")).toBeInTheDocument();
  });

  it("shows a global toast when loading the assistant fails", async () => {
    getPublicAssistant.mockRejectedValueOnce({
      response: { data: { detail: "Load denied" } },
    });
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    render(<PublicAssistantPage />);

    await waitFor(() => {
      expect(
        dispatchSpy.mock.calls.some(
          ([event]) =>
            event.type === "app:toast" &&
            event.detail?.message === "Load denied" &&
            event.detail?.type === "error"
        )
      ).toBe(true);
    });

    expect(screen.queryByText("Load denied")).not.toBeInTheDocument();
    dispatchSpy.mockRestore();
  });

  it("shows a global toast when duplicating the assistant fails", async () => {
    duplicatePublicAssistant.mockRejectedValueOnce({
      response: { data: { detail: "Duplicate denied" } },
    });
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    const user = userEvent.setup();

    render(<PublicAssistantPage />);

    await user.click(await screen.findByRole("button", { name: "Duplicate" }));

    await waitFor(() => {
      expect(
        dispatchSpy.mock.calls.some(
          ([event]) =>
            event.type === "app:toast" &&
            event.detail?.message === "Duplicate denied" &&
            event.detail?.type === "error"
        )
      ).toBe(true);
    });

    expect(screen.queryByText("Duplicate denied")).not.toBeInTheDocument();
    dispatchSpy.mockRestore();
  });
});
