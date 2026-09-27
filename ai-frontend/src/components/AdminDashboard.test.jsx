import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AdminDashboard from "./AdminDashboard";
import {
  getAdminStats,
  getDailyAnalytics,
  getModelUsage,
  getProviderUsage,
  getProviderStatus,
  getProviderLatency,
  getCostUsage,
  getCostBudget,
  getFeedbackAnalytics,
  downloadAnalyticsCsv,
  listAllUsers,
  updateUser,
  deleteUser,
  listAllConversations,
  adminDeleteConversation,
  listAuditLogs,
  listPlans,
  updatePlan,
} from "../lib/adminApi";

vi.mock("recharts", () => {
  const Stub = ({ children }) => <div>{children}</div>;
  return {
    CartesianGrid: Stub,
    Line: Stub,
    LineChart: Stub,
    ResponsiveContainer: Stub,
    Tooltip: Stub,
    XAxis: Stub,
    YAxis: Stub,
  };
});

vi.mock("../lib/adminApi", () => ({
  getAdminStats: vi.fn(),
  getDailyAnalytics: vi.fn(),
  getModelUsage: vi.fn(),
  getProviderUsage: vi.fn(),
  getProviderStatus: vi.fn(),
  getProviderLatency: vi.fn(),
  getCostUsage: vi.fn(),
  getCostBudget: vi.fn(),
  getFeedbackAnalytics: vi.fn(),
  downloadAnalyticsCsv: vi.fn(),
  listAllUsers: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
  listAllConversations: vi.fn(),
  adminDeleteConversation: vi.fn(),
  listAuditLogs: vi.fn(),
  listPlans: vi.fn(),
  updatePlan: vi.fn(),
}));

vi.mock("../lib/errors", () => ({
  getErrorMessage: (_error, fallback) => fallback,
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key, values) =>
      values?.days ? `${key}:${values.days}` : key,
  }),
}));

describe("AdminDashboard", () => {
  beforeEach(() => {
    getAdminStats.mockResolvedValue({
      total_users: 10,
      total_conversations: 20,
      total_messages: 30,
      total_ai_requests: 40,
      total_files: 50,
      storage_used_bytes: 2048,
    });
    getDailyAnalytics.mockResolvedValue([
      {
        date: "2026-09-27",
        new_users: 1,
        new_conversations: 2,
        input_tokens: 3,
        output_tokens: 4,
      },
    ]);
    getModelUsage.mockResolvedValue([
      {
        model: "model-test",
        requests: 5,
        input_tokens: 6,
        output_tokens: 7,
        total_tokens: 13,
      },
    ]);
    getProviderUsage.mockResolvedValue([
      {
        provider: "provider-usage",
        requests: 8,
        input_tokens: 9,
        output_tokens: 10,
        total_tokens: 19,
      },
    ]);
    getProviderStatus.mockResolvedValue([
      {
        role: "primary",
        provider: "provider-status",
        model: "model-status",
        configured: true,
        recent_requests: 11,
        last_request_at: "2026-09-27T00:00:00Z",
        avg_latency_ms: 12,
      },
    ]);
    getProviderLatency.mockResolvedValue([
      {
        provider: "provider-latency",
        requests: 14,
        avg_latency_ms: 125,
        min_latency_ms: 50,
        max_latency_ms: 250,
      },
    ]);
    getCostUsage.mockResolvedValue([
      {
        provider: "provider-cost",
        model: "model-cost",
        requests: 2,
        input_cost_usd: 0.123456,
        output_cost_usd: 0.234567,
        total_cost_usd: 0.358023,
      },
    ]);
    getCostBudget.mockResolvedValue({
      month_start: "2026-09-01",
      budget_usd: 10,
      spent_usd: 1,
      remaining_usd: 9,
      usage_percent: 10,
      over_budget: false,
      unpriced_requests: 0,
    });
    getFeedbackAnalytics.mockResolvedValue({
      total_rated: 4,
      positive: 3,
      negative: 1,
      positive_rate: 75,
    });
    downloadAnalyticsCsv.mockResolvedValue(undefined);
    listAllUsers.mockResolvedValue([]);
    updateUser.mockResolvedValue({});
    deleteUser.mockResolvedValue({});
    listAllConversations.mockResolvedValue([]);
    adminDeleteConversation.mockResolvedValue({});
    listAuditLogs.mockResolvedValue([]);
    listPlans.mockResolvedValue([]);
    updatePlan.mockResolvedValue({});
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("maps every analytics response to the correct section", async () => {
    render(<AdminDashboard currentUserId={1} onClose={vi.fn()} />);

    expect(await screen.findByText("provider-status")).toBeInTheDocument();
    expect(screen.getByText("provider-latency")).toBeInTheDocument();
    expect(screen.getByText("125 ms")).toBeInTheDocument();
    expect(screen.getByText("provider-cost")).toBeInTheDocument();
    expect(screen.getByText("0.358023")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
  });

  it("shows a global toast when analytics loading fails", async () => {
    getAdminStats.mockRejectedValue(new Error("stats failed"));
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    render(<AdminDashboard currentUserId={1} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "app:toast",
          detail: { message: "admin.statsError", type: "error" },
        })
      );
    });

    dispatchSpy.mockRestore();
  });
});
