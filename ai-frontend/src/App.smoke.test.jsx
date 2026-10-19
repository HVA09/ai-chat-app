import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

vi.mock("./components/AuthForm", () => ({
  default: ({ onAuthenticated }) => (
    <button type="button" onClick={onAuthenticated}>Authenticate test session</button>
  ),
}));

vi.mock("./components/SidebarModern", () => ({
  default: ({ onCreateAssistant }) => (
    <button type="button" onClick={onCreateAssistant}>Open assistant editor</button>
  ),
}));

vi.mock("./components/AssistantEditor", () => ({
  default: () => <div data-testid="assistant-editor" />,
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

  it("clears user-scoped overlays before the next login", async () => {
    restoreSession.mockResolvedValueOnce("test-token");

    const { container } = render(<App />);

    await waitFor(() => {
      expect(container.querySelector(".app-shell")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Open assistant editor" }));
    expect(screen.getByTestId("assistant-editor")).toBeInTheDocument();

    act(() => {
      window.dispatchEvent(
        new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true })
      );
    });
    expect(screen.getByTestId("command-palette")).toHaveAttribute("data-open", "true");

    await act(async () => {
      window.dispatchEvent(new Event("auth:unauthorized"));
      await Promise.resolve();
    });

    const authenticateButton = await screen.findByRole("button", {
      name: "Authenticate test session",
    });
    expect(screen.queryByTestId("assistant-editor")).not.toBeInTheDocument();

    fireEvent.click(authenticateButton);

    await waitFor(() => {
      expect(container.querySelector(".app-shell")).toBeInTheDocument();
    });

    expect(screen.getByTestId("command-palette")).toHaveAttribute("data-open", "false");
    expect(screen.queryByTestId("assistant-editor")).not.toBeInTheDocument();
  });
});
