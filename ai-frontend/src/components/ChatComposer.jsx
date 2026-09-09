import { useTranslation } from "react-i18next";

// لازم يطابق حد ChatRequest.message بالباكيند (Field max_length=4000) — بدونه المستخدم
// يقدر يبعت رسالة أطول من المسموح ويوصله خطأ 422 بدل ما نمنعه من الأساس
const MAX_MESSAGE_LENGTH = 4000;

export default function ChatComposer({ value, setValue, onSend, onStop, loading }) {
  const { t } = useTranslation();
  const nearLimit = value.length > MAX_MESSAGE_LENGTH - 200;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!value.trim() || loading) return;
        onSend();
      }}
      className="border-t border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"
    >
      <div className="flex items-end gap-3">
        <div className="flex-1">
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={t("placeholder")}
            rows={2}
            maxLength={MAX_MESSAGE_LENGTH}
            disabled={loading}
            className="min-h-[56px] w-full resize-none rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-400 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
          />
          {nearLimit && (
            <p className="mt-1 text-end text-xs text-slate-400">
              {value.length}/{MAX_MESSAGE_LENGTH}
            </p>
          )}
        </div>
        {loading ? (
          <button
            type="button"
            onClick={onStop}
            className="rounded-2xl border border-red-200 bg-red-50 px-5 py-3 text-red-700 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-400 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
          >
            {t("stop")}
          </button>
        ) : (
          <button
            type="submit"
            disabled={!value.trim()}
            className="rounded-2xl bg-slate-900 px-5 py-3 text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          >
            {t("send")}
          </button>
        )}
      </div>
    </form>
  );
}
