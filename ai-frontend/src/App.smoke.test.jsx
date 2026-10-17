import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./lib/api", async () => {
  const actual = await vi.importActual("./lib/api");
  return {
    ...actual,
    restoreSession: vi.fn().mockRejectedValue(new Error("No active test session")),
  };
});

/*
 * Keep the authenticated-shell smoke test independent from real API failures.
 * These list requests can finish after the jsdom environment is torn down,
 * producing late React updates that fail with "window is not defined".
 */
vi.mock("./lib/usersApi", async () => {
  const actual = await vi.importActual("./lib/usersApi");
  return { ...actual, getCurrentUser: vi.fn().mockResolvedValue(null) };
});

vi.mock("./lib/bookmarksApi", async () => {
  const actual = await vi.importActual("./lib/bookmarksApi");
  return { ...actual, listBookmarkedMessages: vi.fn().mockResolvedValue([]) };
});

vi.mock("./lib/tagsApi", async () => {
  const actual = await vi.importActual("./lib/tagsApi");
  return { ...actual, listTags: vi.fn().mockResolvedValue([]) };
});

vi.mock("./lib/savedPromptsApi", async () => {
  const actual = await vi.importActual("./lib/savedPromptsApi");
  return { ...actual, listSavedPrompts: vi.fn().mockResolvedValue([]) };
});

vi.mock("./hooks/useNotifications", () => ({
  default: () => ({
    notifications: [],
    resetNotifications: () => {},
    refreshNotifications: async () => {},
    handleMarkNotificationRead: async () => {},
    handleMarkAllNotificationsRead: async () => {},
  }),
}));

vi.mock("./components/CommandPalette", () => ({
  default: ({ open }) => (
    <div data-testid="command-palette" data-open={String(open)} />
  ),
}));

import { restoreSession } from "./lib/api";
import App from "./App";

describe("App initial render", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
    restoreSession.mockReset();
    restoreSession.mockRejectedValue(new Error("No active test session"));
  });

  it("renders before session restoration without a temporal-dead-zone error", async () => {
    await act(async () => {
      expect(() => render(<App />)).not.toThrow();
      await Promise.resolve();
    });
  });

  it("keeps the command palette mounted in the authenticated app shell", async () => {
    restoreSession.mockResolvedValueOnce("test-token");

    const { container } = render(<App />);

    await waitFor(() => {
      expect(container.querySelector(".app-shell")).toBeInTheDocument();
    });

    expect(screen.getByTestId("command-palette")).toBeInTheDocument();
  });
});
