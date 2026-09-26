import { render, screen, waitFor } from "@testing-library/react";
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
        "workspaceQuota.title": "Workspace AI request limit",
        "workspaceQuota.description": "Optional workspace cap",
        "workspaceQuota.unlimited": "No workspace limit",
        "workspaceQuota.save": "Save limit",
        "workspaceQuota.hint": "Applies to all workspace members.",
      };
      const value = map[key] ?? key;
      return values
        ? value.replace(/{{(\w+)}}/g, (_, name) => String(values[name]))
        : value;
    },
  }),
}));

vi.mock("../lib/workspaceMembersApi", () => mocks);
const workspaceApiMocks = vi.hoisted(() => ({
  updateWorkspaceDefaultModel: vi.fn(),
  updateWorkspaceDailyLimit: vi.fn(),
}));

vi.mock("../lib/workspacesApi", () => workspaceApiMocks);

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
    workspaceApiMocks.updateWorkspaceDefaultModel.mockReset();
    workspaceApiMocks.updateWorkspaceDailyLimit.mockReset();
    workspaceApiMocks.updateWorkspaceDailyLimit.mockResolvedValue({
      id: 7,
      name: "Demo",
      role: "owner",
      default_ai_model: null,
      daily_ai_request_limit: 40,
    });
    workspaceApiMocks.updateWorkspaceDefaultModel.mockResolvedValue({
      id: 7,
      name: "Demo",
      role: "owner",
      default_ai_model: "gpt-test",
      daily_ai_request_limit: 25,
    });
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
        dailyAiRequestLimit={25}
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


  it("updates the workspace daily AI request limit", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceMembersPanel
        workspaceId={7}
        workspaceName="Demo"
        workspaceRole="owner"
        dailyAiRequestLimit={25}
        onWorkspaceUpdated={vi.fn()}
        onClose={vi.fn()}
      />
    );

    const input = await screen.findByDisplayValue("25");
    await user.clear(input);
    await user.type(input, "40");
    await user.click(screen.getByRole("button", { name: "Save limit" }));
    expect(screen.getByDisplayValue("40")).toBeInTheDocument();
  });

  it("uses the global toast event for quota update errors", async () => {
  const user = userEvent.setup();
  const dispatchSpy = vi.spyOn(window, "dispatchEvent");
  workspaceApiMocks.updateWorkspaceDailyLimit.mockRejectedValueOnce({
    response: { data: { detail: "Quota failed" } },
  });

  render(
    <WorkspaceMembersPanel
      workspaceId={7}
      workspaceName="Demo"
      workspaceRole="owner"
      dailyAiRequestLimit={25}
      onClose={vi.fn()}
    />
  );

  const input = await screen.findByDisplayValue("25");
  await user.click(screen.getByRole("button", { name: "Save limit" }));

  expect(dispatchSpy).toHaveBeenCalledWith(
    expect.objectContaining({
      type: "app:toast",
      detail: { message: "Quota failed", type: "error" },
    })
  );
  dispatchSpy.mockRestore();
});


  it("shows a toast when loading workspace data fails", async () => {
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    mocks.listWorkspaceMembers.mockRejectedValueOnce({
      response: { data: { detail: "Members failed" } },
    });

    render(
      <WorkspaceMembersPanel
        workspaceId={7}
        workspaceName="Demo"
        workspaceRole="owner"
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "app:toast",
          detail: { message: "Members failed", type: "error" },
        })
      );
    });
    dispatchSpy.mockRestore();
  });

  it("shows a toast when inviting a member fails", async () => {
    const user = userEvent.setup();
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    mocks.inviteWorkspaceMember.mockRejectedValueOnce({
      response: { data: { detail: "Invite failed" } },
    });

    render(
      <WorkspaceMembersPanel
        workspaceId={7}
        workspaceName="Demo"
        workspaceRole="owner"
        onClose={vi.fn()}
      />
    );

    const email = await screen.findByPlaceholderText("Email");
    await user.type(email, "member@example.com");
    await user.click(screen.getByRole("button", { name: "Invite" }));

    await waitFor(() => {
      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "app:toast",
          detail: { message: "Invite failed", type: "error" },
        })
      );
    });
    dispatchSpy.mockRestore();
  });
