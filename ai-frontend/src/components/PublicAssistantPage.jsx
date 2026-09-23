import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  duplicatePublicAssistant,
  getPublicAssistant,
} from "../lib/publicAssistantsApi";

function tokenFromPath() {
  const match = window.location.pathname.match(/^\/public-assistant\/([^/]+)\/?$/);
  return match ? decodeURIComponent(match[1]) : "";
}

export default function PublicAssistantPage() {
  const { t } = useTranslation();
  const [assistant, setAssistant] = useState(null);
  const [loading, setLoading] = useState(true);
  const [duplicating, setDuplicating] = useState(false);
  const [error, setError] = useState("");

  const token = tokenFromPath();

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    getPublicAssistant(token)
      .then((data) => {
        if (active) setAssistant(data);
      })
      .catch((err) => {
        if (active) {
          setAssistant(null);
          setError(err?.response?.data?.detail || t("publicAssistant.loadError"));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token, t]);

  const handleDuplicate = async () => {
    setDuplicating(true);
    setError("");
    try {
      await duplicatePublicAssistant(token);
      window.location.assign("/");
    } catch (err) {
      if (err?.response?.status === 401) {
        setError(t("publicAssistant.loginRequired"));
      } else {
        setError(err?.response?.data?.detail || t("publicAssistant.duplicateError"));
      }
    } finally {
      setDuplicating(false);
    }
  };

  return (
    <div className="min-h-full bg-slate-50 px-4 py-8 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <div className="mx-auto max-w-2xl">
        <a
          href="/"
          className="text-sm text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
        >
          ← {t("publicAssistant.backToApp")}
        </a>

        <div className="mt-5 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900 sm:p-8">
          {loading ? (
            <p className="text-sm text-slate-400">...</p>
          ) : assistant ? (
            <>
              <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-900 text-2xl text-white dark:bg-slate-100 dark:text-slate-900">
                🤖
              </div>
              <h1 className="text-2xl font-bold">{assistant.name}</h1>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600 dark:text-slate-300">
                {assistant.description || t("publicAssistant.noDescription")}
              </p>

              <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                {t("publicAssistant.safeNotice")}
              </div>

              <div className="mt-6 flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={handleDuplicate}
                  disabled={duplicating}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
                >
                  {duplicating
                    ? t("publicAssistant.duplicating")
                    : t("publicAssistant.duplicate")}
                </button>
                <a
                  href="/"
                  className="rounded-2xl border border-slate-200 px-4 py-3 text-center text-sm font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  {t("publicAssistant.backToApp")}
                </a>
              </div>

              {error ? (
                <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
                  {error}
                </p>
              ) : null}
            </>
          ) : (
            <div>
              <h1 className="text-xl font-semibold">{t("publicAssistant.notFoundTitle")}</h1>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{error}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
