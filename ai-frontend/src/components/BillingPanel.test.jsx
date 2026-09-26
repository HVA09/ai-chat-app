import { render, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import BillingPanel from "./BillingPanel";

const {
  getPlans,
  getMySubscription,
  getUsage,
  createCheckout,
  cancelSubscription,
} = vi.hoisted(() => ({
  getPlans: vi.fn(),
  getMySubscription: vi.fn(),
  getUsage: vi.fn(),
  createCheckout: vi.fn(),
  cancelSubscription: vi.fn(),
}));

vi.mock("../lib/billingApi", () => ({
  getPlans,
  getMySubscription,
  getUsage,
  createCheckout,
  cancelSubscription,
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) => key,
  }),
}));

vi.mock("../lib/errors", () => ({
  getErrorMessage: vi.fn((_error, fallback) => fallback),
}));

describe("BillingPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getPlans.mockResolvedValue([]);
    getMySubscription.mockResolvedValue(null);
    getUsage.mockResolvedValue(null);
    createCheckout.mockResolvedValue({ checkout_url: "https://example.com/checkout" });
    cancelSubscription.mockResolvedValue({});
  });

  it("shows a global toast when billing data fails to load", async () => {
    getPlans.mockRejectedValue(new Error("billing unavailable"));
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    render(<BillingPanel onClose={vi.fn()} />);

    await waitFor(() => {
      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "app:toast",
          detail: { message: "billing.loadError", type: "error" },
        })
      );
    });

    dispatchSpy.mockRestore();
  });
});
