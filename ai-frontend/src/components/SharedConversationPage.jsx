import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import ChatMessage from "./ChatMessage";
import { getSharedConversation } from "../lib/sharedConversationsApi";

function extractToken() {
  const parts = window.location.pathname.split("/").filter(Boolean);
  if (parts[0] !== "share" || !parts[1]) return "";
  return decodeURIComponent(parts[1]);
}

export default function SharedConversationPage() {
  const { i18n, t } = useTranslation();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const token = extractToken();

  useEffect(() => {
    let active = true;
    getSharedConversation(token)
      .then((response) => {
        if (active) setData(response);
      })
      .catch((err) => {
        if (!active) return;
        setError(
          err?.status === 410
            ? t("sharing.expired")
            : t("sharing.notFound")
        );
      });
    return () => {
      active = false;
    };
  }, [token, t]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4 dark:bg-slate-950">
        <div className="w-full max-w-xl rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
            {t("sharing.invalidTitle")}
          </h1>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-950">
        <p className="text-sm text-slate-500 dark:text-slate-400">{t("sharing.loading")}</p>
      </div>
    );
  }

  return (
    <div
      dir={i18n.language === "ar" ? "rtl" : "ltr"}
      className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100"
    >
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 p-4 backdrop-blur dark:border-slate-700 dark:bg-slate-900/95">
        <div className="mx-auto max-w-4xl">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{t("sharing.badge")}</p>
          <h1 className="mt-1 text-xl font-semibold">{data.title}</h1>
          {data.expires_at ? (
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              {t("sharing.expiresAt", {
                date: new Date(data.expires_at).toLocaleString(),
              })}
            </p>
          ) : null}
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-4 p-4 sm:p-6">
        {data.messages.map((message, index) => (
          <ChatMessage
            key={index}
            role={message.role}
            text={message.content}
            time={new Date(message.created_at).toLocaleTimeString()}
            sources={message.sources || []}
          />
        ))}
        <p className="pb-8 text-center text-xs text-slate-400">{t("sharing.readOnly")}</p>
      </main>
    </div>
  );
}
