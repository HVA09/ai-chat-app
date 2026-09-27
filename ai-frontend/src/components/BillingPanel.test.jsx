import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import BillingPanel from "./BillingPanel";

const {
  cancelSubscription,
  createCheckout,
  getMySubscription,
  getPlans,
  getUsage,
} = vi.hoisted(() => ({
  cancelSubscription: vi.fn(),
  createCheckout: vi.fn(),
  getMySubscription: vi.fn(),
  getPlans: vi.fn(),
  getUsage: vi.fn(),
}));

vi.mock("../lib/billingApi", () => ({
  cancelSubscription,
  createCheckout,
  getMySubscription,
  getPlans,
  getUsage,
}));

vi.mock("react-i18next", () => ({
  initReactI18next: { type: "3rdParty" },
  useTranslation: () => ({
    t: (key) =>
      ({
        "billing.title": "الاشتراك",
        "billing.loadError": "تعذر تحميل بيانات الاشتراك.",
        "billing.checkoutError": "تعذر بدء الدفع.",
        "billing.cancelError": "تعذر إلغاء الاشتراك.",
        "billing.free": "مجاني",
        "billing.perMonth": "شهريًا",
        "billing.perYear": "سنويًا",
        "billing.usageTitle": "الاستخدام",
        "billing.usageLast24h": "آخر 24 ساعة",
        "billing.usageRequests": "الطلبات",
        "billing.usageUnlimited": "غير محدود",
        "billing.usageRemaining": "متبقية",
        "billing.usageTokens": "إجمالي الرموز",
        "billing.usageInputTokens": "رموز الإدخال",
        "billing.usageOutputTokens": "رموز الإخراج",
        "billing.currentPlanLabel": "الخطة الحالية:",
        "billing.renewal": "التجديد:",
        "billing.cancelSubscription": "إلغاء الاشتراك",
        "billing.confirmCancel": "إلغاء الاشتراك؟",
        "billing.currentPlanBadge": "الخطة الحالية",
        "billing.subscribe": "اشترك",
        "billing.requestsPerDay": "طلب/يوم",
      })[key] ?? key,
  }),
}));

describe("BillingPanel", () => {
  it("does not render a stray undefined value", async () => {
    render(<BillingPanel onClose={vi.fn()} />);
    await waitFor(() => {
      expect(screen.queryByText("undefined", { exact: true })).not.toBeInTheDocument();
    });
  });

  beforeEach(() => {
    vi.clearAllMocks();
    getPlans.mockResolvedValue([
      {
        id: "pro",
        name: "Pro",
        price_cents: 1000,
        currency: "usd",
        interval: "month",
        daily_ai_request_limit: 100,
      },
    ]);
    getMySubscription.mockResolvedValue(null);
    getUsage.mockResolvedValue({
      used_requests: 5,
      daily_limit: 100,
      remaining_requests: 95,
      total_tokens: 20,
      input_tokens: 10,
      output_tokens: 10,
    });
    cancelSubscription.mockResolvedValue({});
    createCheckout.mockResolvedValue({
      checkout_url: "https://example.com/checkout",
    });
  });

  it("يستخدم Global Toast عند فشل تحميل بيانات الاشتراك", async () => {
    getPlans.mockRejectedValue({
      response: { data: { detail: "رفض الوصول" } },
    });
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    render(<BillingPanel onClose={vi.fn()} />);

    await waitFor(() => {
      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "app:toast",
          detail: { message: "رفض الوصول", type: "error" },
        })
      );
    });

    dispatchSpy.mockRestore();
  });

  it("يستخدم Global Toast عند فشل بدء الدفع", async () => {
    createCheckout.mockRejectedValue({
      response: { data: { detail: "تعذر إنشاء جلسة الدفع" } },
    });
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    const user = userEvent.setup();

    render(<BillingPanel onClose={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "اشترك" }));

    await waitFor(() => {
      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "app:toast",
          detail: { message: "تعذر إنشاء جلسة الدفع", type: "error" },
        })
      );
    });

    dispatchSpy.mockRestore();
  });

  it("يستخدم Global Toast عند فشل إلغاء الاشتراك", async () => {
    getMySubscription.mockResolvedValue({
      status: "active",
      plan: { id: "pro", name: "Pro" },
    });
    cancelSubscription.mockRejectedValue({
      response: { data: { detail: "لا يمكن إلغاء الاشتراك الآن" } },
    });
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();

    render(<BillingPanel onClose={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: "إلغاء الاشتراك" }));

    await waitFor(() => {
      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "app:toast",
          detail: { message: "لا يمكن إلغاء الاشتراك الآن", type: "error" },
        })
      );
    });

    confirmSpy.mockRestore();
    dispatchSpy.mockRestore();
  });
});
