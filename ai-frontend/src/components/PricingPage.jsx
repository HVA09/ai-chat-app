import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getPlans } from "../lib/billingApi";

function formatPrice(cents, currency, interval, t) {
  if (cents === 0) return t("pricing.free");
  const amount = (cents / 100).toFixed(2);
  const intervalLabel = interval === "year" ? t("pricing.perYear") : t("pricing.perMonth");
  return `${amount} ${String(currency || "usd").toUpperCase()} / ${intervalLabel}`;
}

export default function PricingPage() {
  const { t } = useTranslation();
  const [plans, setPlans] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPlans()
      .then(setPlans)
      .catch(() => setError(t("pricing.loadError")))
      .finally(() => setLoading(false));
  }, [t]);

  return (
    <div className="min-h-full bg-slate-50 px-4 py-10 dark:bg-slate-950">
      <div className="mx-auto max-w-3xl">
        <a href="/" className="text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">
          {t("pricing.backToApp")}
        </a>
        <h1 className="mt-4 text-3xl font-semibold text-slate-900 dark:text-slate-100">{t("pricing.title")}</h1>
        <p className="mt-2 text-slate-500">{t("pricing.subtitle")}</p>

        {loading && <p className="mt-8 text-slate-400">...</p>}
        {error && (
          <div className="mt-8 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900"
            >
              <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">{plan.name}</h2>
              <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">
                {formatPrice(plan.price_cents, plan.currency, plan.interval, t)}
              </p>
              <p className="mt-3 text-sm text-slate-500">
                {plan.daily_ai_request_limit} {t("pricing.requestsPerDay")}
              </p>
              <ul className="mt-4 space-y-1 text-sm text-slate-600 dark:text-slate-300">
                <li>• {t("pricing.savedConversations")}</li>
                <li>• {t("pricing.fileUploads")}</li>
                {plan.price_cents > 0 ? (
                  <li>• {t("pricing.priorityUsage")}</li>
                ) : (
                  <li>• {t("pricing.goodForTrying")}</li>
                )}
              </ul>
              <a
                href="/"
                className="mt-6 inline-block w-full rounded-xl bg-slate-900 px-4 py-2.5 text-center text-sm text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900"
              >
                {t("pricing.startFromApp")}
              </a>
            </div>
          ))}
        </div>

        <p className="mt-8 text-center text-xs text-slate-400">
          {t("pricing.agreeText")}{" "}
          <a className="underline" href="/terms">
            {t("auth.termsLink")}
          </a>{" "}
          {t("pricing.and")}{" "}
          <a className="underline" href="/privacy">
            {t("auth.privacyLink")}
          </a>
          .
        </p>
      </div>
    </div>
  );
}
