import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useTranslation } from "react-i18next";

function CodeBlock({ className, children }) {
  const match = /language-(\w+)/.exec(className || "");
  return match ? (
    <SyntaxHighlighter language={match[1]} style={oneLight} PreTag="div">
      {String(children).replace(/\n$/, "")}
    </SyntaxHighlighter>
  ) : (
    <code className="rounded bg-slate-100 px-1 py-0.5">{children}</code>
  );
}

export default function ChatMessage({
  role,
  text,
  time,
  canRegenerate = false,
  onRegenerate,
  canEdit = false,
  onEdit,
  canDelete = false,
  onDelete,
  sources = [],
  feedback = null,
  canFeedback = false,
  onFeedback,
}) {
  const isUser = role === "user";
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const copyMessage = async () => {
    if (!text || !navigator.clipboard) return;

    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // تجاهل فشل النسخ؛ لا نوقف المحادثة بسببه.
    }
  };

  const editLabel = document.documentElement.lang === "ar" ? "تعديل" : "Edit";
  const deleteLabel = document.documentElement.lang === "ar" ? "حذف" : "Delete";
  const copyLabel = document.documentElement.lang === "ar"
    ? copied
      ? "تم النسخ"
      : "نسخ"
    : copied
      ? "Copied"
      : "Copy";

  const regenerateLabel = document.documentElement.lang === "ar"
    ? "إعادة التوليد"
    : "Regenerate";
  const goodFeedbackLabel = t("feedback.helpful");
  const badFeedbackLabel = t("feedback.notHelpful");

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
          isUser
            ? "bg-slate-900 text-white"
            : "border border-slate-200 bg-white text-slate-900"
        }`}
      >
        <div className="mb-2 flex items-center justify-between gap-3 text-xs opacity-70">
          <div className="flex items-center gap-2">
            <span>{isUser ? t("you") : t("assistant")}</span>
            <span>•</span>
            <span>{time}</span>
          </div>

          {isUser && (canEdit || canDelete) ? (
            <div className="flex items-center gap-1">
              {canEdit && onEdit ? (
                <button
                  type="button"
                  onClick={onEdit}
                  className="rounded-md px-2 py-1 text-xs font-medium transition hover:bg-white/10 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-slate-300"
                  aria-label={editLabel}
                  title={editLabel}
                >
                  {editLabel}
                </button>
              ) : null}
              {canDelete && onDelete ? (
                <button
                  type="button"
                  onClick={onDelete}
                  className="rounded-md px-2 py-1 text-xs font-medium transition hover:bg-white/10 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-slate-300"
                  aria-label={deleteLabel}
                  title={deleteLabel}
                >
                  {deleteLabel}
                </button>
              ) : null}
            </div>
          ) : null}

          {!isUser && text ? (
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={copyMessage}
                className="rounded-md px-2 py-1 text-xs font-medium transition hover:bg-slate-100 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
                aria-label={copyLabel}
                title={copyLabel}
              >
                {copyLabel}
              </button>
              {canRegenerate && onRegenerate ? (
                <button
                  type="button"
                  onClick={onRegenerate}
                  className="rounded-md px-2 py-1 text-xs font-medium transition hover:bg-slate-100 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
                  aria-label={regenerateLabel}
                  title={regenerateLabel}
                >
                  {regenerateLabel}
                </button>
              ) : null}
              {canDelete && onDelete ? (
                <button
                  type="button"
                  onClick={onDelete}
                  className="rounded-md px-2 py-1 text-xs font-medium transition hover:bg-slate-100 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-slate-400"
                  aria-label={deleteLabel}
                  title={deleteLabel}
                >
                  {deleteLabel}
                </button>
              ) : null}
            </div>
          ) : null}
        </div>

        <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ code: CodeBlock }}>
          {text}
        </ReactMarkdown>

        {!isUser && canFeedback ? (
          <div className="mt-3 flex items-center gap-1 border-t border-slate-200 pt-2 dark:border-slate-700">
            <button
              type="button"
              onClick={() => onFeedback?.(1)}
              className={`rounded-lg px-2 py-1 text-sm transition hover:bg-slate-100 dark:hover:bg-slate-800 ${feedback === 1 ? "bg-slate-100 dark:bg-slate-800" : ""}`}
              aria-label={goodFeedbackLabel}
              title={goodFeedbackLabel}
            >
              👍
            </button>
            <button
              type="button"
              onClick={() => onFeedback?.(-1)}
              className={`rounded-lg px-2 py-1 text-sm transition hover:bg-slate-100 dark:hover:bg-slate-800 ${feedback === -1 ? "bg-slate-100 dark:bg-slate-800" : ""}`}
              aria-label={badFeedbackLabel}
              title={badFeedbackLabel}
            >
              👎
            </button>
            {feedback !== null ? (
              <span className="ms-1 text-xs text-slate-400">{t("feedback.saved")}</span>
            ) : null}
          </div>
        ) : null}

        {!isUser && sources.length > 0 ? (
          <div className="mt-3 border-t border-slate-200 pt-2 dark:border-slate-700">
            <div className="mb-1 text-xs font-semibold text-slate-500 dark:text-slate-400">
              {t("sources.title")}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {sources.map((source) => {
                const label = source.filename || source.title || source.url || source.id;
                const text = `[${source.id}] ${label}${source.chunk ? ` · ${t("sources.chunkShort", { chunk: source.chunk })}` : ""}`;
                const content = source.url ? (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-600 hover:underline dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                    title={source.snippet || (source.chunk ? t("sources.chunkTooltip", { chunk: source.chunk }) : source.url)}
                  >
                    {text}
                  </a>
                ) : (
                  <span
                    className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                    title={source.snippet || (source.chunk ? t("sources.chunkTooltip", { chunk: source.chunk }) : label)}
                  >
                    {text}
                  </span>
                );
                return <span key={source.id}>{content}</span>;
              })}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
