import { useState } from "react";
import { useTranslation } from "react-i18next";

const STEPS = [
  { id: "chat", icon: "💬", action: "newChat" },
  { id: "organize", icon: "📁", action: "organize" },
  { id: "knowledge", icon: "📚", action: "files" },
];

export default function OnboardingModal({
  onClose,
  onNewChat,
  onOpenFiles,
  onOpenAccount,
}) {
  const { t } = useTranslation();
  const [step, setStep] = useState(0);
  const current = STEPS[step];

  const handleAction = () => {
    if (current.action === "newChat") onNewChat?.();
    if (current.action === "organize") onOpenAccount?.();
    if (current.action === "files") onOpenFiles?.();
    onClose?.();
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/50 p-4 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-title"
        className="w-full max-w-lg overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900"
      >
        <div className="p-6 sm:p-8">
          <div className="mb-5 flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                {t("onboarding.stepCounter", { current: step + 1, total: STEPS.length })}
              </p>
              <h2
                id="onboarding-title"
                className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100"
              >
                {t("onboarding.title")}
              </h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label={t("onboarding.close")}
              className="rounded-xl px-2 py-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            >
              ✕
            </button>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-center dark:border-slate-700 dark:bg-slate-800">
            <div className="text-4xl" aria-hidden="true">{current.icon}</div>
            <h3 className="mt-3 text-lg font-semibold text-slate-900 dark:text-slate-100">
              {t(`onboarding.steps.${current.id}.title`)}
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
              {t(`onboarding.steps.${current.id}.description`)}
            </p>
          </div>

          <div className="mt-5 flex gap-2">
            {STEPS.map((item, index) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setStep(index)}
                aria-label={t("onboarding.goToStep", { step: index + 1 })}
                className={`h-2 flex-1 rounded-full transition ${
                  index === step
                    ? "bg-slate-900 dark:bg-slate-100"
                    : "bg-slate-200 dark:bg-slate-700"
                }`}
              />
            ))}
          </div>

          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl px-4 py-2.5 text-sm font-medium text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
            >
              {t("onboarding.skip")}
            </button>

            <div className="flex gap-2">
              {step > 0 ? (
                <button
                  type="button"
                  onClick={() => setStep((currentStep) => currentStep - 1)}
                  className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  {t("onboarding.back")}
                </button>
              ) : null}
              {step < STEPS.length - 1 ? (
                <button
                  type="button"
                  onClick={() => setStep((currentStep) => currentStep + 1)}
                  className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
                >
                  {t("onboarding.next")}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleAction}
                  className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
                >
                  {t(`onboarding.steps.${current.id}.action`)}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
