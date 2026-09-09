import LegalPageShell from "./LegalPageShell";

export default function PrivacyPage() {
  return (
    <LegalPageShell title="سياسة الخصوصية">
      <p>
        توضح هذه السياسة كيف نتعامل مع بياناتك عند استخدام الخدمة. نسعى لجمع الحد الأدنى اللازم
        لتشغيل الحساب وتحسين التجربة.
      </p>
      <h2 className="mt-6 text-base font-semibold text-slate-900 dark:text-slate-100">ما نجمعه</h2>
      <ul className="list-disc pe-5">
        <li>البريد الإلكتروني وبيانات الحساب (مثل الاسم الاختياري).</li>
        <li>محتوى المحادثات والملفات التي ترفعها لتشغيل الميزات.</li>
        <li>سجلات تقنية محدودة (مثل وقت الطلب وعنوان IP مبسّط للحماية من الإساءة).</li>
        <li>بيانات الاشتراك عبر مزوّد الدفع (لا نخزّن أرقام البطاقات كاملة لدينا).</li>
      </ul>
      <h2 className="mt-6 text-base font-semibold text-slate-900 dark:text-slate-100">كيف نستخدمها</h2>
      <ul className="list-disc pe-5">
        <li>تقديم الخدمة والمصادقة والأمان.</li>
        <li>إرسال رسائل ضرورية (تفعيل البريد، إعادة التعيين، تنبيهات الاشتراك).</li>
        <li>تحسين الأداء ومراقبة الإساءة ضمن الحد المعقول.</li>
      </ul>
      <h2 className="mt-6 text-base font-semibold text-slate-900 dark:text-slate-100">المشاركة مع أطراف ثالثة</h2>
      <p>
        قد تُرسل أجزاء من المحادثة إلى مزوّد الذكاء الاصطناعي الذي تختاره المنشأة لتشغيل الردود.
        كذلك نستخدم مزوّدي دفع واستضافة وفق عقودهم. لا نبيع بياناتك الشخصية.
      </p>
      <h2 className="mt-6 text-base font-semibold text-slate-900 dark:text-slate-100">الاحتفاظ والحذف</h2>
      <p>
        يمكنك طلب حذف الحساب من الإعدادات. عند الحذف نسعى لإزالة بيانات الحساب المرتبطة وفق
        الإمكانيات التقنية والالتزامات القانونية.
      </p>
      <h2 className="mt-6 text-base font-semibold text-slate-900 dark:text-slate-100">التواصل</h2>
      <p>لطلبات الخصوصية: privacy@example.com</p>
    </LegalPageShell>
  );
}
