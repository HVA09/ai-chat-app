import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { confirmEmailVerification } from "../lib/authApi";
import { getErrorMessage } from "../lib/errors";

export default function VerifyEmailPage() {
  const { t } = useTranslation();
  const [status, setStatus] = useState("loading"); // loading | success | error
  const [message, setMessage] = useState("");

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) {
      setStatus("error");
      setMessage(t("verifyEmail.missingLink"));
      return;
    }
    confirmEmailVerification(token)
      .then((data) => {
        setStatus("success");
        setMessage(data.detail);
      })
      .catch((err) => {
        setStatus("error");
        setMessage(getErrorMessage(err, t("verifyEmail.genericError")));
      });
  }, [t]);

  return (
    <div className="flex h-full items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-sm rounded-3xl border border-slate-200 bg-white p-6 text-center shadow-sm">
        {status === "loading" && <p className="text-slate-500">{t("verifyEmail.verifying")}</p>}
        {status === "success" && (
          <>
            <h1 className="mb-2 text-lg font-semibold text-emerald-700">{t("verifyEmail.successTitle")}</h1>
            <p className="text-sm text-slate-500">{message}</p>
          </>
        )}
        {status === "error" && (
          <>
            <h1 className="mb-2 text-lg font-semibold text-red-700">{t("verifyEmail.errorTitle")}</h1>
            <p className="text-sm text-slate-500">{message}</p>
          </>
        )}
        <a
          href="/"
          className="mt-4 inline-block rounded-xl bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800"
        >
          {t("verifyEmail.backToApp")}
        </a>
      </div>
    </div>
  );
}
