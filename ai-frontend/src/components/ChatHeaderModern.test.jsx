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
