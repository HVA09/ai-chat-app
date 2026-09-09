import LegalPageShell from "./LegalPageShell";

export default function TermsPage() {
  return (
    <LegalPageShell title="شروط الاستخدام">
      <p>
        باستخدامك لهذا التطبيق («الخدمة») فإنك توافق على هذه الشروط. إذا لم توافق، يرجى عدم
        استخدام الخدمة.
      </p>
      <h2 className="mt-6 text-base font-semibold text-slate-900 dark:text-slate-100">الحساب</h2>
      <p>
        أنت مسؤول عن سرية بيانات الدخول وتفعيل التحقق الثنائي عند الحاجة. يحق لنا تعليق أو إغلاق
        الحسابات التي تنتهك الشروط أو تُسيء استخدام الموارد.
      </p>
      <h2 className="mt-6 text-base font-semibold text-slate-900 dark:text-slate-100">الاستخدام المقبول</h2>
      <ul className="list-disc pe-5">
        <li>لا تستخدم الخدمة لأنشطة غير قانونية أو ضارة.</li>
        <li>لا تحاول اختراق الأنظمة أو تجاوز حدود الاستخدام.</li>
        <li>المحتوى الذي ترسله يبقى مسؤوليتك.</li>
      </ul>
      <h2 className="mt-6 text-base font-semibold text-slate-900 dark:text-slate-100">الاشتراكات والدفع</h2>
      <p>
        الخطط المدفوعة تُجدَّد حسب الدورة المختارة عبر مزوّد الدفع. يمكنك الإلغاء من لوحة الاشتراك؛
        وقد تسري قيود الخطة المجانية فور الإلغاء حسب إعدادات النظام.
      </p>
      <h2 className="mt-6 text-base font-semibold text-slate-900 dark:text-slate-100">إخلاء المسؤولية</h2>
      <p>
        الردود المولَّدة بالذكاء الاصطناعي قد تحتوي أخطاء. لا تعتمد عليها كاستشارة طبية أو قانونية
        أو مالية دون تحقق مستقل.
      </p>
      <h2 className="mt-6 text-base font-semibold text-slate-900 dark:text-slate-100">التواصل</h2>
      <p>للاستفسارات المتعلقة بالشروط: support@example.com</p>
    </LegalPageShell>
  );
}
