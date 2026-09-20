import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { cancelSubscription, createCheckout, getMySubscription, getPlans } from "../lib/billingApi";
import { getErrorMessage } from "../lib/errors";

function formatPrice(cents, currency, interval, t) {
  if (cents === 0) return t("billing.free");
  const amount = (cents / 100).toFixed(2);
  const intervalLabel = interval === "month" ? t("billing.perMonth") : t("billing.perYear");
  return `${amount} ${currency.toUpperCase()} / ${intervalLabel}`;
}

export default function BillingPanel({ onClose }) {
  const { t } = useTranslation();
  const [plans, setPlans] = useState([]);
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyPlanId, setBusyPlanId] = useState(null);
  const [error, setError] = useState("");

  const refresh = async () => {
    setLoading(true);
    try {
      const [plansData, subData] = await Promise.all([getPlans(), getMySubscription()]);
      setPlans(plansData);
      setSubscription(subData);
    } catch {
      setError(t("billing.loadError"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleSubscribe = async (planId) => {
    setError("");
    setBusyPlanId(planId);
    try {
      const { checkout_url } = await createCheckout(planId);
      window.location.href = checkout_url;
    } catch (err) {
      setError(getErrorMessage(err, t("billing.checkoutError")));
      setBusyPlanId(null);
    }
  };

  const handleCancel = async () => {
    if (!window.confirm(t("billing.confirmCancel"))) return;
    setError("");
    try {
      await cancelSubscription();
      await refresh();
    } catch {
      setError(t("billing.cancelError"));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/30 p-4">
      <div className="my-8 w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">{t("billing.title")}</h2>
          <button
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ✕
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-slate-400">...</p>
        ) : (
          <>
            {subscription && subscription.status === "active" && (
              <div className="mb-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                <p className="text-sm text-emerald-800">
                  {t("billing.currentPlanLabel")} <span className="font-medium">{subscription.plan.name}</span>
                </p>
                {subscription.current_period_end && (
                  <p className="mt-1 text-xs text-emerald-700">
                    {t("billing.renewal")} {new Date(subscription.current_period_end).toLocaleDateString()}
                  </p>
                )}
                <button
                  onClick={handleCancel}
                  className="mt-3 rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50"
                >
                  {t("billing.cancelSubscription")}
                </button>
              </div>
            )}

            {error && (
              <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </div>
            )}

            <div className="space-y-3">
              {plans.map((plan) => {
                const isCurrentPlan =
                  subscription?.status === "active" && subscription.plan.id === plan.id;
                return (
                  <div
                    key={plan.id}
                    className={`rounded-2xl border p-4 ${
                      isCurrentPlan ? "border-slate-900" : "border-slate-200"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-slate-900">{plan.name}</p>
                        <p className="text-sm text-slate-500">
                          {formatPrice(plan.price_cents, plan.currency, plan.interval, t)}
                        </p>
                        <p className="mt-1 text-xs text-slate-400">
                          {plan.daily_ai_request_limit} {t("billing.requestsPerDay")}
                        </p>
                      </div>
                      {isCurrentPlan ? (
                        <span className="rounded-full bg-slate-900 px-3 py-1 text-xs text-white">
                          {t("billing.currentPlanBadge")}
                        </span>
                      ) : plan.price_cents > 0 ? (
                        <button
                          onClick={() => handleSubscribe(plan.id)}
                          disabled={busyPlanId === plan.id}
                          className="rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
                        >
                          {busyPlanId === plan.id ? "..." : t("billing.subscribe")}
                        </button>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
