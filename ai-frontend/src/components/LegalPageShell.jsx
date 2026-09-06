import { useTranslation } from "react-i18next";

// ملاحظة: هاد الـshell (الرابط، العنوان، تاريخ التحديث) مترجَم بالكامل، لكن نص "children"
// (محتوى الشروط/الخصوصية الفعلي) يبقى عربي فقط عن قصد — ترجمة نص قانوني بدقة تحتاج
// مراجعة مختص، مو استبدال آلي للنصوص متل باقي واجهة التطبيق.
export default function LegalPageShell({ title, children }) {
  const { t, i18n } = useTranslation();
  return (
    <div className="min-h-full bg-slate-50 px-4 py-10 dark:bg-slate-950">
      <div className="mx-auto max-w-2xl rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900 sm:p-8">
        <a href="/" className="text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">
          {t("legal.backToApp")}
        </a>
        <h1 className="mt-4 text-2xl font-semibold text-slate-900 dark:text-slate-100">{title}</h1>
        <div className="prose prose-slate mt-6 max-w-none text-sm leading-7 text-slate-600 dark:text-slate-300">
          {children}
        </div>
        <p className="mt-8 text-xs text-slate-400">
          {t("legal.lastUpdated", {
            date: new Date().toLocaleDateString(i18n.language === "ar" ? "ar" : "en-US"),
          })}
        </p>
      </div>
    </div>
  );
}
