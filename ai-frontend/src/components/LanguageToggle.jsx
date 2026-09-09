import { useTranslation } from "react-i18next";

export default function LanguageToggle({ lang, setLang }) {
  const { t } = useTranslation();

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-slate-500">{t("language")}</span>
      <button
        onClick={() => setLang(lang === "ar" ? "en" : "ar")}
        className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm hover:bg-slate-100"
      >
        {lang === "ar" ? t("english") : t("arabic")}
      </button>
    </div>
  );
}
