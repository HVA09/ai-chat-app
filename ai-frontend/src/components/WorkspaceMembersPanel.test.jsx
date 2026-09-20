import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import WorkspaceMembersPanel from "./WorkspaceMembersPanel";

const mocks = vi.hoisted(() => ({
  listWorkspaceMembers: vi.fn(),
  listWorkspaceInvitations: vi.fn(),
  listWorkspaceAuditLogs: vi.fn(),
  getWorkspaceUsage: vi.fn(),
  downloadWorkspaceUsageCsv: vi.fn(),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key, values) => {
      const map = {
        "workspaceMembers.title": "Workspace members",
        "workspaceMembers.inviteTitle": "Invite a member",
        "workspaceMembers.membersTitle": "Members",
        "workspaceMembers.pendingTitle": "Pending invitations",
        "workspaceMembers.activityTitle": "Workspace activity",
        "workspaceMembers.noMembers": "No other members",
        "workspaceMembers.noPending": "No pending invitations",
        "workspaceMembers.noActivity": "No activity recorded yet",
        "workspaceMembers.existingUserOnly": "Existing users only",
        "workspaceMembers.emailPlaceholder": "Email",
        "workspaceMembers.memberRole": "Member",
        "workspaceMembers.adminRole": "Admin",
        "workspaceMembers.invite": "Invite",
        "workspaceMembers.remove": "Remove",
        "workspaceMembers.revoke": "Revoke",
        "workspaceMembers.confirmRemove": "Remove {{email}}?",
        "workspaceUsage.title": "Workspace AI usage",
        "workspaceUsage.window": "Last {{hours}} hours",
        "workspaceUsage.requests": "Requests",
        "workspaceUsage.inputTokens": "Input tokens",
        "workspaceUsage.outputTokens": "Output tokens",
        "workspaceUsage.totalTokens": "Total tokens",
        "workspaceUsage.byMember": "Usage by member",
        "workspaceUsage.noData": "No usage recorded in this period",
        "workspaceUsage.requestsShort": "requests",
        "workspaceUsage.inputShort": "input",
        "workspaceUsage.outputShort": "output",
        "workspaceUsage.totalShort": "total",
        "workspaceUsage.exportCsv": "Export CSV",
        "workspaceUsage.exportError": "Couldn't export usage data",
      };
      const value = map[key] ?? key;
      return values
        ? value.replace(/{{(\w+)}}/g, (_, name) => String(values[name]))
        : value;
    },
  }),
}));

vi.mock("../lib/workspaceMembersApi", () => mocks);

describe("WorkspaceMembersPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listWorkspaceMembers.mockResolvedValue([
      {
        id: 1,
        email: "owner@example.com",
        full_name: "Owner",
        role: "owner",
      },
    ]);
    mocks.listWorkspaceInvitations.mockResolvedValue([]);
    mocks.listWorkspaceAuditLogs.mockResolvedValue([]);
    mocks.downloadWorkspaceUsageCsv.mockResolvedValue(undefined);
    mocks.getWorkspaceUsage.mockResolvedValue({
      workspace_id: 7,
      window_hours: 24,
      window_start: "2026-09-20T00:00:00Z",
      used_requests: 5,
      input_tokens: 40,
      output_tokens: 60,
      total_tokens: 100,
      members: [
        {
          user_id: 1,
          email: "owner@example.com",
          full_name: "Owner",
          used_requests: 5,
          input_tokens: 40,
          output_tokens: 60,
          total_tokens: 100,
        },
      ],
    });
  });

  it("renders aggregated workspace AI usage for managers", async () => {
    render(
      <WorkspaceMembersPanel
        workspaceId={7}
        workspaceName="Demo"
        workspaceRole="owner"
        onClose={vi.fn()}
      />
    );

    expect(await screen.findByText("Workspace AI usage")).toBeInTheDocument();
    expect(screen.getByText("5", { exact: true })).toBeInTheDocument();
    const totalTokensLabel = screen.getByText(/Total tokens/);
    expect(totalTokensLabel.parentElement?.textContent).toContain("100");
    expect(screen.getAllByText("Owner", { exact: true }).length).toBeGreaterThan(0);
  });

  it("exports workspace usage as CSV", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceMembersPanel
        workspaceId={7}
        workspaceName="Demo"
        workspaceRole="owner"
        onClose={vi.fn()}
      />
    );

    await user.click(await screen.findByRole("button", { name: "Export CSV" }));
    expect(mocks.downloadWorkspaceUsageCsv).toHaveBeenCalledWith(7, 24);
  });

});
