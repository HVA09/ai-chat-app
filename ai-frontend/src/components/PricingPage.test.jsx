import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import PricingPage from "./PricingPage";

const { getPlans } = vi.hoisted(() => ({
  getPlans: vi.fn(),
}));

vi.mock("../lib/billingApi", () => ({
  getPlans,
}));

vi.mock("../lib/errors", () => ({
  getErrorMessage: vi.fn((error, fallback) => error?.response?.data?.detail || fallback),
}));

vi.mock("react-i18next", () => ({
  initReactI18next: { type: "3rdParty" },
  useTranslation: () => ({
    t: (key) =>
      ({
        "pricing.backToApp": "الرجوع للتطبيق",
        "pricing.title": "الأسعار",
        "pricing.subtitle": "اختر الخطة المناسبة",
        "pricing.loadError": "تعذر تحميل الخطط",
        "pricing.requestsPerDay": "طلب/يوم",
        "pricing.savedConversations": "المحادثات المحفوظة",
        "pricing.fileUploads": "رفع الملفات",
        "pricing.priorityUsage": "أولوية أعلى",
        "pricing.goodForTrying": "مناسب للتجربة",
        "pricing.startFromApp": "ابدأ من التطبيق",
        "pricing.agreeText": "بالتسجيل أنت توافق على",
        "pricing.and": "و",
        "pricing.free": "مجاني",
        "pricing.perMonth": "شهريًا",
        "pricing.perYear": "سنويًا",
        "auth.termsLink": "الشروط",
        "auth.privacyLink": "الخصوصية",
      })[key] ?? key,
  }),
}));

describe("PricingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getPlans.mockResolvedValue([
      {
        id: "free",
        name: "Free",
        price_cents: 0,
        currency: "usd",
        interval: "month",
        daily_ai_request_limit: 10,
      },
    ]);
  });

  it("renders available plans", async () => {
    render(<PricingPage />);

    expect(await screen.findByRole("heading", { name: "Free" })).toBeInTheDocument();
    expect(screen.getByText("10 طلب/يوم")).toBeInTheDocument();
  });

  it("uses Global Toast when plan loading fails", async () => {
    getPlans.mockRejectedValue({
      response: { data: { detail: "تعذر الوصول إلى الخطط" } },
    });
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    render(<PricingPage />);

    await waitFor(() => {
      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "app:toast",
          detail: { message: "تعذر الوصول إلى الخطط", type: "error" },
        })
      );
    });

    expect(screen.queryByText("تعذر الوصول إلى الخطط")).not.toBeInTheDocument();
    dispatchSpy.mockRestore();
  });
});
