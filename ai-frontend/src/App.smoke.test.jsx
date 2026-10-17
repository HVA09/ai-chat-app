import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./lib/api", () => {
  const request = () => vi.fn().mockResolvedValue({ data: [] });
  return {
    default: {
      get: request(),
      post: request(),
      put: request(),
      patch: request(),
      delete: request(),
      request: request(),
    },
    restoreSession: vi.fn().mockRejectedValue(new Error("No active test session")),
  };
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
