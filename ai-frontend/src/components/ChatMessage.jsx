import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useTranslation } from "react-i18next";
function CodeBlock({ className, children }) { const match = /language-(\w+)/.exec(className || ""); return match ? <SyntaxHighlighter language={match[1]} style={oneLight} PreTag="div">{String(children).replace(/\n$/, "")}</SyntaxHighlighter> : <code className="rounded bg-slate-100 px-1 py-0.5">{children}</code>; }
export default function ChatMessage({ role, text, time }) { const isUser = role === "user"; const { t } = useTranslation(); return <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}><div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-sm ${isUser ? "bg-slate-900 text-white" : "border border-slate-200 bg-white text-slate-900"}`}><div className="mb-2 flex items-center gap-2 text-xs opacity-70"><span>{isUser ? t("you") : t("assistant")}</span><span>•</span><span>{time}</span></div><ReactMarkdown remarkPlugins={[remarkGfm]} components={{ code: CodeBlock }}>{text}</ReactMarkdown></div></div>; }
