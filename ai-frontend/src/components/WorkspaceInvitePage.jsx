import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { restoreSession } from "../lib/api";
import { acceptWorkspaceInvitation } from "../lib/workspaceMembersApi";

export default function WorkspaceInvitePage() {
  const { t } = useTranslation();
  const [status, setStatus] = useState("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) {
      setStatus("error");
      setMessage(t("workspaceInvite.invalid"));
      return;
    }

    (async () => {
      try {
        await restoreSession();
        const result = await acceptWorkspaceInvitation(token);
        setStatus("success");
        setMessage(t("workspaceInvite.accepted", { workspace: result.workspace_name }));
      } catch (error) {
        setStatus("error");
        setMessage(
          error?.response?.status === 401
            ? t("workspaceInvite.loginFirst")
            : t("workspaceInvite.error")
        );
      }
    })();
  }, [t]);

  return (
    <div className="flex min-h-full items-center justify-center bg-slate-50 p-4 dark:bg-slate-950">
      <div className="w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-6 shadow-lg dark:border-slate-700 dark:bg-slate-900">
        <h1 className="text-xl font-semibold">{t("workspaceInvite.title")}</h1>
        <p className="mt-3 text-sm text-slate-500">{message || "..."}</p>
        {status !== "loading" && (
          <a href="/" className="mt-5 inline-flex rounded-xl bg-slate-900 px-4 py-2 text-sm text-white">
            {t("workspaceInvite.backToApp")}
          </a>
        )}
      </div>
    </div>
  );
}
