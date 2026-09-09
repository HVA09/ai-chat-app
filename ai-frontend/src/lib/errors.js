/**
 * FastAPI بترجع شكلين مختلفين لحقل "detail" بجسم استجابة الخطأ:
 *  - نص (string) عادي: من HTTPException(detail="...") — مثل "بريد أو كلمة مرور غير صحيحة"
 *  - مصفوفة (array) من objects: من خطأ تحقق Pydantic التلقائي (422) — كل عنصر فيه
 *    msg/loc/type، مثل رفض كلمة مرور ضعيفة أو رسالة أطول من الحد المسموح
 *
 * لو "detail" مصفوفة وعُرضت مباشرة داخل JSX (`{error}`)، React بيرمي خطأ "Objects are
 * not valid as a React child" وينهار المكوّن كامل (وبما إن ErrorBoundary ملفوف حوالين
 * التطبيق كله بـ main.jsx، الانهيار بيوصل للتطبيق بالكامل مش بس للفورم).
 *
 * detailToMessage() توحّد الشكلين لنص واحد آمن — تاخذ قيمة "detail" مباشرة (لاستخدامها
 * مع fetch() الخام متل تدفّق الشات). getErrorMessage() هي الغلاف المستخدَم مع أخطاء axios
 * (اللي بتيجي بشكل err.response.data.detail) وهو الاستخدام الأكثر شيوعًا بالتطبيق.
 */
import i18n from "../i18n";

export function detailToMessage(detail, fallback) {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const messages = detail
      .map((item) => {
        const raw = typeof item?.msg === "string" ? item.msg : "";
        // Pydantic v2 بيحط بادئة "Value error, " بالإنجليزي قبل أي رسالة من validator
        // مخصص (متل شرط قوة كلمة المرور) — نشيلها عشان ما تختلط برسالة عربية
        return raw.replace(/^Value error,\s*/i, "").trim();
      })
      .filter(Boolean);
    if (messages.length > 0) {
      const separator = i18n.language === "ar" ? "، " : ", ";
      return messages.join(separator);
    }
  }

  return fallback;
}

export function getErrorMessage(err, fallback) {
  return detailToMessage(err?.response?.data?.detail, fallback);
}

export default getErrorMessage;
