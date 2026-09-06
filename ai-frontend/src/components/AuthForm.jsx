import { useState } from "react";
import { useTranslation } from "react-i18next";
import { loginUser, registerUser, requestPasswordReset } from "../lib/authApi";
import { getErrorMessage } from "../lib/errors";

export default function AuthForm({ onAuthenticated }) {
  const { t } = useTranslation();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [needsTotp, setNeedsTotp] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);
  const switchMode = (nextMode) => { setMode(nextMode); setError(""); setInfo(""); setNeedsTotp(false); setTotpCode(""); };
  const completeLogin = async () => { await loginUser(email, password, needsTotp ? totpCode : null); onAuthenticated(); };
  const submit = async (e) => {
    e.preventDefault(); setError(""); setInfo(""); setLoading(true);
    try { if (mode === "forgot") { const data = await requestPasswordReset(email); setInfo(data.detail); return; } if (mode === "register") await registerUser(email, password); await completeLogin(); }
    catch (err) { if (err.response?.status === 428) { setNeedsTotp(true); setError(""); return; } setError(getErrorMessage(err, t("auth.genericError"))); }
    finally { setLoading(false); }
  };
  const titles = { login: needsTotp ? t("auth.totpTitle") : t("auth.loginTitle"), register: t("auth.registerTitle"), forgot: t("auth.forgotTitle") };
  return <div className="flex h-full items-center justify-center bg-slate-50 p-4 dark:bg-slate-950"><form onSubmit={submit} className="w-full max-w-sm rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900"><h1 className="mb-1 text-xl font-semibold text-slate-900 dark:text-slate-100">{t("appName")}</h1><p className="mb-5 text-sm text-slate-500">{titles[mode]}</p>{needsTotp ? <input type="text" required autoFocus inputMode="numeric" maxLength={6} placeholder={t("auth.totpPlaceholder")} value={totpCode} onChange={(e) => setTotpCode(e.target.value)} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-center tracking-[0.5em] outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100" /> : <div className="space-y-3"><input type="email" required placeholder={t("auth.emailPlaceholder")} value={email} onChange={(e) => setEmail(e.target.value)} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100" />{mode !== "forgot" && <input type="password" required minLength={8} placeholder={t("auth.passwordPlaceholder")} value={password} onChange={(e) => setPassword(e.target.value)} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100" />}</div>}{mode === "login" && !needsTotp && <button type="button" onClick={() => switchMode("forgot")} className="mt-2 text-sm text-slate-500 hover:text-slate-700">{t("auth.forgotPassword")}</button>}{error && <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}{info && <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{info}</div>}<button type="submit" disabled={loading} className="mt-4 w-full rounded-xl bg-slate-900 px-4 py-2.5 text-white hover:bg-slate-800 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1">{loading ? "..." : needsTotp ? t("auth.confirm") : mode === "login" ? t("auth.login") : mode === "register" ? t("auth.register") : t("auth.sendResetLink")}</button>{needsTotp ? <button type="button" onClick={() => switchMode("login")} className="mt-3 w-full text-center text-sm text-slate-500 hover:text-slate-700">{t("auth.back")}</button> : mode === "forgot" ? <button type="button" onClick={() => switchMode("login")} className="mt-3 w-full text-center text-sm text-slate-500 hover:text-slate-700">{t("auth.backToLogin")}</button> : <button type="button" onClick={() => switchMode(mode === "login" ? "register" : "login")} className="mt-3 w-full text-center text-sm text-slate-500 hover:text-slate-700">{mode === "login" ? t("auth.noAccount") : t("auth.haveAccount")}</button>}<p className="mt-4 text-center text-xs text-slate-400"><a href="/pricing" className="underline hover:text-slate-600">{t("auth.pricingLink")}</a>{" · "}<a href="/terms" className="underline hover:text-slate-600">{t("auth.termsLink")}</a>{" · "}<a href="/privacy" className="underline hover:text-slate-600">{t("auth.privacyLink")}</a></p></form></div>;
}
