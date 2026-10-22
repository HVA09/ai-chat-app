import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ChatHeaderModern from "./ChatHeaderModern";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) =>
      ({
        appName: "AI Assistant",
        newChat: "New chat",
        "header.more": "More",
        "header.account": "Account",
        "header.files": "Files",
        "header.billing": "Billing",
        logout: "Logout",
        "sharing.shareButton": "Share",
        "sharing.manageButton": "Manage shares",
        "workspaceSharing.shareButton": "Share workspace",
        "workspaceSharing.unshareButton": "Unshare workspace",
        exportMarkdown: "Export Markdown",
        exportJson: "Export JSON",
        "conversationTitle.generateButton": "Generate title",
        "conversationTitle.loading": "Generating...",
        "summary.button": "Summarize",
        "summary.loading": "Summarizing...",
        "chat.branchListTitle": "View branches",
        "chat.parentConversation": "Parent conversation",
      })[key] ?? key,
  }),
}));

vi.mock("./LanguageToggle", () => ({ default: () => null }));
vi.mock("./ThemeToggle", () => ({ default: () => null }));
vi.mock("./NotificationBell", () => ({ default: () => null }));
vi.mock("./ui/Icon", () => ({ default: () => <span aria-hidden="true" /> }));

function renderHeader(overrides = {}) {
  const props = {
    conversationTitle: "",
    lang: "en",
    setLang: vi.fn(),
    onLogout: vi.fn(),
    onOpenAccount: vi.fn(),
    onOpenFiles: vi.fn(),
    onOpenAdmin: vi.fn(),
    onOpenBilling: vi.fn(),
    onShareConversation: vi.fn(),
    canShareConversation: false,
    onManageShares: vi.fn(),
    canManageShares: false,
    onToggleWorkspaceShare: vi.fn(),
    canShareWithWorkspace: false,
    workspaceShareActive: false,
    onExportConversation: vi.fn(),
    canExportConversation: false,
    onSummarizeConversation: vi.fn(),
    canSummarizeConversation: false,
    summaryLoading: false,
    onGenerateConversationTitle: vi.fn(),
    canGenerateConversationTitle: false,
    titleLoading: false,
    conversationBranches: [],
    onOpenConversationBranch: vi.fn(),
    parentConversationId: null,
    onOpenParentConversation: vi.fn(),
    isAdmin: false,
    notifications: [],
    onMarkNotificationRead: vi.fn(),
    onMarkAllNotificationsRead: vi.fn(),
    ...overrides,
  };
  render(<ChatHeaderModern {...props} />);
  return props;
}

describe("ChatHeaderModern contextual conversation actions", () => {
  it("does not render the conversation more button when no conversation action is available", () => {
    renderHeader();
    expect(screen.queryByRole("button", { name: "More" })).not.toBeInTheDocument();
  });

  it("renders the conversation more button when an action is available", async () => {
    const user = userEvent.setup();
    renderHeader({ canExportConversation: true });

    await user.click(screen.getByRole("button", { name: "More" }));

    expect(screen.getByRole("button", { name: "Export Markdown" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export JSON" })).toBeInTheDocument();
  });
});

describe("ChatHeaderModern mobile navigation", () => {
  it("closes the settings menu on Escape and restores focus to its trigger", async () => {
    const user = userEvent.setup();
    renderHeader();

    const settingsButton = screen.getByRole("button", { name: "Settings" });
    await user.click(settingsButton);
    expect(screen.getByRole("button", { name: "Account" })).toBeInTheDocument();

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("button", { name: "Account" })).not.toBeInTheDocument();
    expect(settingsButton).toHaveAttribute("aria-expanded", "false");
    expect(settingsButton).toHaveFocus();
  });

  it("closes conversation actions after an outside pointer interaction", async () => {
    const user = userEvent.setup();
    renderHeader({ canExportConversation: true });

    const moreButton = screen.getByRole("button", { name: "More" });
    await user.click(moreButton);
    expect(screen.getByRole("button", { name: "Export Markdown" })).toBeInTheDocument();

    await user.click(document.body);

    expect(screen.queryByRole("button", { name: "Export Markdown" })).not.toBeInTheDocument();
    expect(moreButton).toHaveAttribute("aria-expanded", "false");
  });

  it("keeps header popovers mutually exclusive and labels the branches control", async () => {
    const user = userEvent.setup();
    renderHeader({
      canExportConversation: true,
      conversationBranches: [{ id: 9, title: "A branch" }],
    });

    const settingsButton = screen.getByRole("button", { name: "Settings" });
    const moreButton = screen.getByRole("button", { name: "More" });
    const branchesButton = screen.getByRole("button", { name: "View branches" });

    await user.click(settingsButton);
    await user.click(moreButton);
    expect(screen.queryByRole("button", { name: "Account" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export Markdown" })).toBeInTheDocument();

    await user.click(branchesButton);
    expect(screen.queryByRole("button", { name: "Export Markdown" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "A branch" })).toBeInTheDocument();
    expect(branchesButton).toHaveAttribute("aria-expanded", "true");
  });
});

describe("ChatHeaderModern mobile navigation", () => {
  it("dispatches the sidebar-open event from the mobile menu button", async () => {
    const user = userEvent.setup();
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    renderHeader();

    await user.click(screen.getByRole("button", { name: "Open navigation" }));

    expect(dispatchSpy).toHaveBeenCalledWith(
      expect.objectContaining({ type: "app:open-sidebar" })
    );
    dispatchSpy.mockRestore();
  });
});
