import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import ChatHeader from "./ChatHeader";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) => ({
      appName: "AI Assistant",
      emptyDesc: "Start chatting",
      logout: "Logout",
      "chat.parentConversation": "Parent conversation",
      "chat.parentConversationTitle": "Open the parent conversation",
      "chat.branches": "Branches",
      "chat.branchListTitle": "View branches",
      "chat.branchListEmpty": "No branches",
      "conversationTitle.generateButton": "Generate title",
      "conversationTitle.loading": "Generating...",
      "conversationTitle.disabled": "Start a conversation first",
    })[key] ?? key,
  }),
}));

vi.mock("./LanguageToggle", () => ({ default: () => null }));
vi.mock("./ThemeToggle", () => ({ default: () => null }));
vi.mock("./NotificationBell", () => ({ default: () => null }));

function renderHeader(overrides = {}) {
  const props = {
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
  render(<ChatHeader {...props} />);
  return props;
}

describe("ChatHeader parent conversation navigation", () => {
  it("shows the parent button for a branched conversation and opens the parent", async () => {
    const user = userEvent.setup();
    const { onOpenParentConversation } = renderHeader({ parentConversationId: 41 });

    await user.click(screen.getByRole("button", { name: "Parent conversation" }));

    expect(onOpenParentConversation).toHaveBeenCalledWith(41);
  });

  it("generates a conversation title when enabled", async () => {
    const user = userEvent.setup();
    const { onGenerateConversationTitle } = renderHeader({
      canGenerateConversationTitle: true,
    });

    await user.click(screen.getByRole("button", { name: "Generate title" }));

    expect(onGenerateConversationTitle).toHaveBeenCalled();
  });

  it("does not show the parent button for a root conversation", () => {
    renderHeader();
    expect(screen.queryByRole("button", { name: "Parent conversation" })).not.toBeInTheDocument();
  });
});
