import { useState } from "react";
import { useTranslation } from "react-i18next";
import { confirmPasswordReset } from "../lib/authApi";
import { getErrorMessage } from "../lib/errors";

export default function ResetPasswordPage() {
  const { t } = useTranslation();
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("idle"); // idle | success | error
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const token = new URLSearchParams(window.location.search).get("token");

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      const data = await confirmPasswordReset(token, password);
      setStatus("success");
      setMessage(data.detail);
    } catch (err) {
      setStatus("error");
      setMessage(getErrorMessage(err, t("resetPassword.genericError")));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-sm rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="mb-4 text-lg font-semibold text-slate-900">{t("resetPassword.title")}</h1>

        {!token && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {t("resetPassword.invalidLink")}
          </div>
        )}

        {token && status !== "success" && (
          <form onSubmit={submit} className="space-y-3">
            <input
              type="password"
              required
              minLength={8}
              placeholder={t("resetPassword.newPasswordPlaceholder")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400"
            />
            {message && status === "error" && (
              <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {message}
              </div>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-slate-900 px-4 py-2.5 text-white hover:bg-slate-800 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1"
            >
              {loading ? "..." : t("resetPassword.submit")}
            </button>
          </form>
        )}

        {status === "success" && (
          <div>
            <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              {message}
            </div>
            <a
              href="/"
              className="block w-full rounded-xl bg-slate-900 px-4 py-2.5 text-center text-sm text-white hover:bg-slate-800"
            >
              {t("resetPassword.goToLogin")}
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
